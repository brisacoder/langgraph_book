import asyncio
import shutil
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Annotated, List, Sequence
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from colorama import Fore, Style


class State(TypedDict):
    messages: Annotated[list, add_messages]


async def generation_node(state: State) -> State:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an helpful assistant doing critical work, attention to detail is important"
                " If the user provides critique, respond with a revised version of your previous attempts.",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    llm = ChatOpenAI()
    generate = prompt | llm

    return {"messages": [await generate.ainvoke(state["messages"])]}


async def reflection_node(state: State) -> State:
    reflection_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a critique assistant. Generate critique and recommendations for the user's submission."
                "Provide detailed recommendations appropriate for the task",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    llm = ChatOpenAI()    
    reflect = reflection_prompt | llm    
    # Other messages we need to adjust
    cls_map = {"ai": HumanMessage, "human": AIMessage}
    # First message is the original user request. We hold it the same for all nodes
    translated = [state["messages"][0]] + [
        cls_map[msg.type](content=msg.content) for msg in state["messages"][1:]
    ]
    res = await reflect.ainvoke(translated)
    # We treat the output of this as human feedback for the generator
    return {"messages": [HumanMessage(content=res.content)]}

def build_graph() -> CompiledStateGraph:
    builder = StateGraph(State)
    builder.add_node("generate", generation_node)
    builder.add_node("reflect", reflection_node)
    builder.add_edge(START, "generate")


    def should_continue(state: State):
        if len(state["messages"]) > 6:
            # End after 3 iterations
            return END
        return "reflect"


    builder.add_conditional_edges("generate", should_continue)
    builder.add_edge("reflect", "generate")
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    graph.get_state
    return graph


async def process_events(graph: CompiledStateGraph, human_message):
    events = []
    config = {"configurable": {"thread_id": "1"}}
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
        events.append(event)
    return events


def print_events(events):
    colors = [getattr(Fore, attr) for attr in dir(Fore) if attr.isupper()]
    color_map= {}
    num_colors = len(colors)

    # Get terminal width (fall back to 80 if it cannot be determined)
    terminal_width = shutil.get_terminal_size((80, 20)).columns

    for i, event in enumerate(events):
        node = list(event.keys())[0]
        
        # Assign a color for the node if it's not already mapped
        color = color_map.get(node, None)
        if color is None:
            color_map[node] = colors[i % num_colors]
            color = color_map[node]
        
        # Create the centered header
        header = f" {node} ".center(terminal_width, '=')
        print(f"\n{Style.RESET_ALL}{header}{Style.RESET_ALL}")
        
        # Print the event message in the assigned color
        print(f"{color}{node}: {event[node]['messages'][0].content}{Style.RESET_ALL}")


def main():
    load_dotenv()
    graph = build_graph()
    print("Welcome to the ChatGPT Mock Chat! Type 'exit' to quit.\n")
    while True:
        # Get user input
        user_input = input(f"{Fore.BLUE}User: {Style.RESET_ALL}")
        
        # Exit condition
        if user_input.strip().lower() in ['exit', 'quit']:
            print(f"{Fore.GREEN}Assistant: Goodbye!{Style.RESET_ALL}")
            break
        
        # Mock assistant response
        assistant_response = f"You said: '{user_input}'"

        events = asyncio.run(process_events(graph, user_input))
        print_events(events)    
        
        # Display assistant response
        # event['generate']['messages'][0].content
        ai_message = graph.get_state({"configurable": {"thread_id": "1"}}).values["messages"][-1].content
        print(f"\n{Fore.GREEN}Assistant: {ai_message}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()

