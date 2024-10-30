import asyncio
import operator
import os
import shutil
import uuid
import logging
from typing import Dict, List, Any
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
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

MAX_ROUNDS = 3


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


async def generation_node(state: State) -> Dict:
    """
    Generates the assistant's response based on the current state.

    Args:
        state (State): The current conversation state containing messages and rounds.

    Returns:
        State: The updated state with the assistant's response and incremented rounds.

    Notes:
        - Uses the ChatOpenAI model to generate the assistant's reply.
        - If an error occurs, logs the error and returns a default state.
        - Prompt tells LLM to work off last answer, otherwise it constructs a mash up of previous answers
        - Prompt tells LLM to not remove information, otherwise it adds but also removes. 
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant engaged in critical work; attention to detail is essential."
                " When the user provides critique, you will incorporate it into your last answer, keeping in mind: "
                " 1. Always work off your last answer without collating information from previous attempts. "
                " 2. Do not remove information unless it is incorrect. "
                " 3. Ensure that the text flows smoothly and coherently. "
                "Always end your messages with a separating line followed by a final review of the work. ",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"))
    generate = prompt | llm

    try:
        return {"messages": [await generate.ainvoke({"messages": state["messages"]})], "rounds": 1}
    except RuntimeError as e:
        logging.error(f"Error in generation_node: {e}")
        return {"messages": [], "rounds": 1}


async def reflection_node(state: State) -> Dict:
    """
    Generates critique and recommendations based on the assistant's previous response.

    Args:
        state (State): The current conversation state containing messages.

    Returns:
        State: The updated state including the human's critique message.

    Notes:
        - Swaps the roles of AI and human messages to simulate reflection.
        - If an error occurs, logs the error and returns a default state.
    """
    reflection_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a critique assistant. Generate critique and recommendations for the user's submission."
                "Provide detailed recommendations appropriate for the task. If no further improvement are "
                "warranted, clearly state it. Do not nit pick",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"))
    reflect = reflection_prompt | llm
    # Other messages we need to adjust
    cls_map = {"ai": HumanMessage, "human": AIMessage}
    if not state.get("messages"):
        logging.warning("No messages available in state for reflection.")
        return default_state()

    # Proceed with the rest of the function
    first_message = state["messages"][0]
    # First message is the original user request. We hold it the same for all nodes
    translated = [first_message] + [
        cls_map[msg.type](content=msg.content) for msg in state["messages"][1:]
    ]
    try:
        res = await reflect.ainvoke({"messages": translated})
    except RuntimeError as e:
        logging.error(f"Error in reflection_node: {e}")
        return default_state()

    # We treat the output of this as human feedback for the generator
    return {"messages": [HumanMessage(content=res.content)], "rounds": 0}


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
    # builder.add_edge("end", END)

    def should_continue(state: State) -> str:
        """
        Determines whether the conversation should continue or end.

        Args:
            state (State): The current conversation state.

        Returns:
            str: The name of the next node ('end' or 'reflect').
        """
        if state["rounds"] > MAX_ROUNDS:
            return END
        return "reflect"

    builder.add_conditional_edges("generate", should_continue)
    builder.add_edge("reflect", "generate")
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
        print(f"{color}{node}: {event[node]['messages'][0].content}{Style.RESET_ALL}")
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
    config = {"configurable": {"thread_id": uuid.uuid4(), "color_map": build_color_map(graph)}}
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
