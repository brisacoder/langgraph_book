import asyncio
import operator
import os
import shutil
import uuid
import logging
from typing import Dict, List, Any
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.config import RunnableConfig
from typing import Annotated
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from colorama import Fore, Style
from prompts import Prompts

MAX_ROUNDS = 1


def default_state() -> Dict:
    return {
        "messages": [],
        "rounds": 0
    }


# Configure logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class State(TypedDict):
    """
    Represents the state of the conversation.

    Attributes:
        messages (Annotated[List[BaseMessage], add_messages]): A list of messages exchanged in the conversation.
        rounds (Annotated[int, operator.add]): The number of conversation rounds completed.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    rounds: Annotated[int, operator.add]
    cot_prompt: str


async def generation_node(state: State, config: RunnableConfig) -> Dict:
    """
    Generates the assistant's response based on the current state.

    Args:
        state (State): The current conversation state containing messages and rounds.

    Returns:
        State: The updated state with the assistant's response and incremented rounds.

    Notes:
        - Uses the ChatOpenAI model to generate the CoT prompt.
        - If an error occurs, logs the error and returns a default state.
    """
    prompt = ChatPromptTemplate(
        [
            (
                "system",
                "{system_prompt}",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    # default is prompt to generate a CoT prompt
    system_prompt = config["configurable"].get("system_prompt", Prompts.COT)
    partial_prompt = prompt.partial(system_prompt=system_prompt)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"))
    generate = partial_prompt | llm

    try:
        res = await generate.ainvoke({"messages": state["messages"]})
        return {"messages": [res], "rounds": 1, "cot_prompt": res.content}
    except RuntimeError as e:
        logging.error(f"Error in generation_node: {e}")
        return {"messages": [], "rounds": 1}


async def reflection_node(state: State) -> Dict:
    """
    Solves the problem using CoT prompt created by the generate node

    Args:
        state (State): The current conversation state containing messages.

    Returns:
        State: The updated state including the human's critique message.

    Notes:
        - If an error occurs, logs the error and returns a default state.
        - We do not translate ToolMessages or tool_calls
    """

    reflection_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an assistant for question-answering tasks. Use the provided plan to answer the question"),
            ("human", "Question: {question}\nPlan: {plan}"),  # Formatted message
        ]
    )

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"))
    reflect = reflection_prompt | llm
    # Proceed with the rest of the function
    first_message = state["messages"][0]
    plan_message = state["messages"][1]
    try:
        res = await reflect.ainvoke({"question": first_message.content, "plan": plan_message.content})
    except RuntimeError as e:
        logging.error(f"Error in reflection_node: {e}")
        return default_state()

    # We treat the output of this as human feedback for the generator
    return {"messages": [res], "rounds": 0}


async def end_node(state: State) -> Dict:
    """
    Terminates the conversation by negating the rounds count.

    Args:
        state (State): The current conversation state.

    Returns:
        State: The updated state signaling the end of the conversation.
    """
    return {"rounds": -state["rounds"]}


def build_graph() -> CompiledStateGraph:
    """
    Builds and compiles the state graph for the conversation flow.

    Returns:
        CompiledStateGraph: The compiled state graph with nodes and transitions.

    Notes:
        - Defines nodes for generation, reflection, and ending the conversation.
        - Sets up conditional transitions based on the number of rounds.
    """
    builder = StateGraph(State)
    builder.add_node("generate", generation_node)
    builder.add_node("reflect", reflection_node)
    builder.add_node("end", end_node)
    builder.add_edge(START, "generate")
    builder.add_edge("generate", "reflect")
    builder.add_edge("end", END)

    def should_continue(state: State) -> str:
        """
        Determines whether the conversation should continue or end.

        Args:
            state (State): The current conversation state.

        Returns:
            str: The name of the next node ('end' or 'reflect').
        """
        return "end"

    builder.add_conditional_edges("reflect", should_continue)
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    graph.get_state
    return graph


async def print_message(event: Dict[str, Any], config: RunnableConfig):
    """
    Prints the event message to the console with appropriate formatting and color.

    Args:
        event (Dict[str, Any]): The event dictionary containing node and message data.
        config (Dict[str, Any]): The configuration containing color mappings.

    Notes:
        - Adjusts output formatting based on terminal width.
        - Uses color mappings to differentiate nodes.
    """
    node = list(event.keys())[0]
    # Get terminal width (fall back to 80 if it cannot be determined)
    terminal_width = shutil.get_terminal_size((80, 20)).columns
    header = f" {node} ".center(terminal_width, '=')
    print(f"\n{Style.RESET_ALL}{header}{Style.RESET_ALL}")

    # Print the event message in the assigned color
    color = config["configurable"]["color_map"][node]
    if "messages" in event[node] and event[node]["messages"]:
        print(f"{color}{node}: {event[node]['messages'][0]}{Style.RESET_ALL}")
    else:
        logging.warning(f"No messages found in event for node '{node}'")


def build_color_map(graph: CompiledStateGraph) -> Dict[str, str]:
    """
    Builds a mapping of graph nodes to color codes for console output.

    Args:
        graph (CompiledStateGraph): The compiled state graph.

    Returns:
        Dict[str, str]: A dictionary mapping node names to ANSI color codes.

    Notes:
        - Cycles through available colors if there are more nodes than colors.
    """
    nodes = list(graph.nodes.keys())
    colors = [getattr(Fore, attr) for attr in dir(Fore) if attr.isupper()]
    color_map: dict = {}
    num_colors = len(colors)

    for i, node in enumerate(nodes):
        # Assign a color for the node if it's not already mapped
        color = color_map.get(node, None)
        if color is None:
            color_map[node] = colors[i % num_colors]
            color = color_map[node]
    return color_map


async def process_events(graph: CompiledStateGraph, human_message: str, config: RunnableConfig):
    """
    Processes events in the state graph based on the user's input message.
    """
    try:
        async for event in graph.astream(
            {
                "messages": [
                    HumanMessage(
                        content=human_message
                    )
                ],
            },
            config,
        ):
            await print_message(event, config)
    except Exception as e:
        logging.error(f"Error processing events: {e}")


async def main():
    """
    Main function that starts the conversation loop and handles user interaction.

    Notes:
        - Loads environment variables.
        - Initializes the conversation graph and configurations.
        - Continuously prompts the user for input until 'exit' or 'quit' is entered.
    """
    load_dotenv()
    graph = build_graph()
    print("Welcome to the Reflection Chat! Type 'exit' to quit.\n")
    config = {"configurable": {"thread_id": uuid.uuid4(), "color_map": build_color_map(graph),
                               "system_prompt": Prompts.COT}}
    try:
        while True:
            # Get user input
            user_input = input(f"{Fore.BLUE}User: {Style.RESET_ALL}")

            # Exit condition
            if user_input.strip().lower() in ['exit', 'quit']:
                print(f"{Fore.GREEN}Assistant: Goodbye!{Style.RESET_ALL}")
                break

            print(f"\n{Fore.GREEN}Assistant: Gossiping with agents, wait...{Style.RESET_ALL}\n")
            await process_events(graph, user_input, config)

            # Display assistant response
            state = await graph.aget_state(config)
            # After
            if state.values.get("messages") and state.values["messages"]:
                ai_message = state.values["messages"][-1].content
                print(f"\n{Fore.GREEN}Assistant: {ai_message}{Style.RESET_ALL}\n")
            else:
                logging.warning("No messages available in the state to display.")
    except Exception as e:
        logging.error(f"An error occurred in the main loop: {e}")
    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}Assistant: Goodbye!{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main())
