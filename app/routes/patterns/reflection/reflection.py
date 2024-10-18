from ast import Dict
import asyncio
import operator
import shutil
import uuid
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
    rounds: Annotated[int, operator.add]
    start_message: int


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

    return {"messages": [await generate.ainvoke(state["messages"])], "rounds": 1}


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

async def end_node(state: State) -> State:
    return {"rounds": -state["rounds"]}

def build_graph() -> CompiledStateGraph:
    builder = StateGraph(State)
    builder.add_node("generate", generation_node)
    builder.add_node("reflect", reflection_node)
    builder.add_node("end", end_node)
    builder.add_edge(START, "generate")
    builder.add_edge("end", END)



    def should_continue(state: State):
        if state["rounds"] > 3:
            return "end"
        return "reflect"


    builder.add_conditional_edges("generate", should_continue)
    builder.add_edge("reflect", "generate")
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    graph.get_state
    return graph


async def process_events(graph: CompiledStateGraph, human_message: str, config: Dict):
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
        node = list(event.keys())[0]
        # Get terminal width (fall back to 80 if it cannot be determined)
        terminal_width = shutil.get_terminal_size((80, 20)).columns
        header = f" {node} ".center(terminal_width, '=')
        print(f"\n{Style.RESET_ALL}{header}{Style.RESET_ALL}")
        
        # Print the event message in the assigned color
        color = config["configurable"]["color_map"][node]
        if "messages" in event[node]:
            print(f"{color}{node}: {event[node]['messages'][0].content}{Style.RESET_ALL}")


def build_color_map(graph):
    nodes = list(graph.nodes.keys())
    colors = [getattr(Fore, attr) for attr in dir(Fore) if attr.isupper()]
    color_map= {}
    num_colors = len(colors)

    for i, node in enumerate(nodes):
        # Assign a color for the node if it's not already mapped
        color = color_map.get(node, None)
        if color is None:
            color_map[node] = colors[i % num_colors]
            color = color_map[node]
    return color_map


def get_message(event):
    messages = ""
    colors = [getattr(Fore, attr) for attr in dir(Fore) if attr.isupper()]
    color_map= {}
    num_colors = len(colors)

    # Get terminal width (fall back to 80 if it cannot be determined)
    terminal_width = shutil.get_terminal_size((80, 20)).columns

    node = list(event.keys())[0]
    
    # Assign a color for the node if it's not already mapped
    color = color_map.get(node, None)
    if color is None:
        color_map[node] = colors[i % num_colors]
        color = color_map[node]
    
    # Create the centered header
    header = f" {node} ".center(terminal_width, '=')
    messages += f"\n{Style.RESET_ALL}{header}{Style.RESET_ALL}"
    
    # Print the event message in the assigned color
    if "messages" in event[node]:
        messages += f"{color}{node}: {event[node]['messages'][0].content}{Style.RESET_ALL}"

    return messages


def main():
    load_dotenv()
    graph = build_graph()
    print("Welcome to the Reflection Chat! Type 'exit' to quit.\n")
    while True:
        # Get user input
        config = {"configurable": {"thread_id": uuid.uuid4(), "color_map": build_color_map(graph)}}
        user_input = input(f"{Fore.BLUE}User: {Style.RESET_ALL}")
        
        # Exit condition
        if user_input.strip().lower() in ['exit', 'quit']:
            print(f"{Fore.GREEN}Assistant: Goodbye!{Style.RESET_ALL}")
            break

        asyncio.run(process_events(graph, user_input, config))  
        
        # Display assistant response
        ai_message = graph.get_state(config).values["messages"][-1].content
        print(f"\n{Fore.GREEN}Assistant: {ai_message}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()

