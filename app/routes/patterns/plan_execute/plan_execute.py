import logging
import operator
import os
from typing import Annotated, Dict, List, Tuple
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_community.tools.tavily_search import TavilySearchResults
from prompts import Prompts  # type: ignore

# Configure logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str
    messages: Annotated[List[BaseMessage], add_messages]


class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )


async def planner_node(state: PlanExecute, config: RunnableConfig) -> Dict:
    """
    Creates a plan to solve the task.

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
    # default is PLAN_AND_EXECUTE prompt
    system_prompt = config["configurable"].get("system_prompt", Prompts.PLAN_AND_EXECUTE)
    partial_prompt = prompt.partial(system_prompt=system_prompt)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"))
    tool = TavilySearchResults(max_results=2)
    tools = [tool]
    llm_with_tools = llm.bind_tools(tools)
    generate = partial_prompt | llm_with_tools


    try:
        return {"messages": [await generate.ainvoke({"messages": state["messages"]})], "rounds": 1}
    except RuntimeError as e:
        logging.error(f"Error in generation_node: {e}")
        return {"messages": [], "rounds": 1}


async def execute_node(state: PlanExecute, config: RunnableConfig) -> Dict:
    """
    Creates a plan to solve the task.

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
    # default is PLAN_AND_EXECUTE prompt
    system_prompt = config["configurable"].get("system_prompt", Prompts.PLAN_AND_EXECUTE)
    partial_prompt = prompt.partial(system_prompt=system_prompt)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"))
    tool = TavilySearchResults(max_results=2)
    tools = [tool]
    llm_with_tools = llm.bind_tools(tools)
    generate = partial_prompt | llm_with_tools
 
    try:
        return {"messages": [await generate.ainvoke({"messages": state["messages"]})], "rounds": 1}
    except RuntimeError as e:
        logging.error(f"Error in generation_node: {e}")
        return {"messages": [], "rounds": 1}

