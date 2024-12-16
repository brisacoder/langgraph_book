from copy import deepcopy
import json
import logging
import os
from typing import Dict, cast
from dotenv import load_dotenv

MAX_ROUNDS = 2

# Tools imports

from langgraph.prebuilt import ToolNode, tools_condition
from plan_critique import PlanCritique
from tools_api import wrap_as_tool
from search_tools import get_search_tools
from spotify_tools import get_spotify_tools
from plan import Plan, get_plan_tools
from langchain_openai import ChatOpenAI

# System Prompt imports

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    BaseMessage,
    ToolMessage,
)
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
    format="%(asctime)s - %(levelname)s - %(message)s",  # Define the format
    handlers=[logging.StreamHandler()],  # Output to the console
)


def default_state() -> Dict:
    return {"messages": [], "rounds": 0}


async def patch_prompt_node(state: State, config: RunnableConfig) -> Dict:
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

    first_message = state["messages"][0]
    tools = get_spotify_tools() + get_plan_tools() + get_search_tools()
    tools_schema = [wrap_as_tool(tool) for tool in tools]
    prompt_suffix = f"\n- You have access to the following Tools: \n {json.dumps(tools_schema)}"
    new_prompt = HumanMessage(content=first_message.content + prompt_suffix, id=first_message.id)
    return {"messages": new_prompt}


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
    partial_prompt = prompt.partial(system_prompt=Prompts.HUMAN)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"), temperature=1.0)
    llm_with_structure = llm.with_structured_output(schema=Plan, method="json_schema", include_raw=True)
    generate = partial_prompt | llm_with_structure

    try:
        llm_response = await generate.ainvoke({"messages": state["messages"]})
        return {"messages": llm_response["raw"],  "plan": llm_response["parsed"]}
    except RuntimeError as e:
        logging.error(f"Error in generation_node: {e}")
        return {"messages": []}


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
                Prompts.REFLECTION,
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"))
    llm_with_structure = llm.with_structured_output(
        schema=PlanCritique, method="json_schema", include_raw=True
    )
    reflect = reflection_prompt | llm_with_structure
    # Other messages we need to adjust
    cls_map = {"ai": HumanMessage, "human": AIMessage}
    if not state.get("messages"):
        logging.warning("No messages available in state for reflection.")
        return default_state()

    # Proceed with the rest of the function
    first_message = state["messages"][0]
    # First message is the original user request. We hold it the same for all nodes
    try:
        translated = [first_message]
        for msg in state["messages"][1:]:
            # We do not translate AI tool calls or ToolMessages
            if (
                isinstance(msg, AIMessage)
                and hasattr(msg, "tool_calls")
                and len(msg.tool_calls) > 0
            ):
                translated += [msg]
            elif isinstance(msg, ToolMessage):
                translated += [msg]
            else:
                content = msg.content
                translated += [cls_map[msg.type](content=content)]
    except Exception as e:
        logging.error(f"Error translating messages: {e}")

    try:
        llm_response = await reflect.ainvoke({"messages": translated})
    except RuntimeError as e:
        logging.error(f"Error in reflection_node: {e}")
        return default_state()

    # We treat the output of this as human feedback for the generator
    return {"messages": [HumanMessage(content=llm_response["raw"].content)], "rounds": 1}


async def plan_exec_node(state: State, config: RunnableConfig) -> Dict:
    """
    Executes the plan created by the previous nodes in the graph.

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
            (
                "human",
                "{exec_prompt}"
            )
        ]
    )
    partial_prompt = prompt.partial(system_prompt=Prompts.SYSTEM, exec_prompt=Prompts.EXEC)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"), temperature=1.0)
    tools = get_spotify_tools() + get_plan_tools() + get_search_tools()
    llm_with_tools = llm.bind_tools(tools)
    generate = partial_prompt | llm_with_tools

    try:
        llm_response = await generate.ainvoke({"messages": state["messages"]})
        return {"messages": llm_response}
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
    tool_node = ToolNode(get_spotify_tools() + get_plan_tools() + get_search_tools())
    builder.add_node("patch_prompt", patch_prompt_node)
    builder.add_node("planner", planner_node)
    builder.add_node("reflection", reflection_node)
    builder.add_node("plan_exec", plan_exec_node)
    builder.add_node("end", end_node)
    builder.add_edge(START, "patch_prompt")
    builder.add_edge("patch_prompt", "planner")
    builder.add_edge("end", END)

    def should_continue(state: State) -> str:
        """
        Determines whether the conversation should continue or end.

        Args:
            state (State): The current conversation state.

        Returns:
            str: The name of the next node ('end' or 'reflect').
        """
        if state["rounds"] > MAX_ROUNDS:
            return "plan_exec"
        return "reflection"

    builder.add_conditional_edges("planner", should_continue)
    builder.add_edge("reflection", "planner")

    builder.add_node("tools", tool_node)
    builder.add_edge("tools", "plan_exec")
    builder.add_conditional_edges("plan_exec", tools_condition)
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    return graph
