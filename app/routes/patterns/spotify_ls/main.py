import logging
import os
from typing import Dict
from dotenv import load_dotenv

# Tools imports

from langgraph.prebuilt import ToolNode
from spotify_tools import get_spotify_tools
from plan import get_plan_tools
from langchain_openai import ChatOpenAI

# System Prompt imports

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.config import RunnableConfig
from prompts import Prompts

# State

from state import State, get_state
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START


load_dotenv(override=True)
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',  # Define the format
    handlers=[logging.StreamHandler()]  # Output to the console
)


async def planner_node(state: State, config: RunnableConfig) -> Dict:
    """
    Generates the assistant's response based on the current state.

    Args:
        state (State): The current conversation state containing messages and rounds.

    Returns:
        State: The updated state with the assistant's response and incremented rounds.

    Notes:
        - Uses the ChatOpenAI model to generate the assistant's reply.
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
    partial_prompt = prompt.partial(system_prompt=Prompts.SYSTEM)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"), temperature=1.0)
    tools = get_spotify_tools() + get_plan_tools()
    llm_with_tools = llm.bind_tools(tools)
    generate = partial_prompt | llm_with_tools

    try:
        return {"messages": [await generate.ainvoke({"messages": state["messages"]})]}
    except RuntimeError as e:
        logging.error(f"Error in generation_node: {e}")
        return {"messages": []}


async def end_node(state: State) -> Dict:
    """
    Terminates the conversation and cleans up any state.

    Args:
        state (State): The current conversation state.

    Returns:
        State: The updated state signaling the end of the conversation.
    """
    return {"messages": []}


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
    tool_node = ToolNode(get_spotify_tools() + get_plan_tools())
    builder.add_node("planner", planner_node)
    builder.add_node("end", end_node)
    builder.add_edge(START, "planner")
    builder.add_edge("end", END)

    def should_continue(state: State) -> str:
        """
        Determines whether the conversation should continue or end.

        Args:
            state (State): The current conversation state.

        Returns:
            str: The name of the next node ('end' or 'reflect').
        """
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return "end"

    builder.add_node("tools", tool_node)
    builder.add_conditional_edges("planner", should_continue)
    builder.add_edge("tools", "planner")
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    graph.get_state
    return graph
