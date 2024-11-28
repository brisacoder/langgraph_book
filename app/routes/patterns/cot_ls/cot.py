import operator
import os
import logging
from typing import Dict, List
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.config import RunnableConfig
from typing import Annotated
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from prompts import Prompts

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
    cot_prompt: str


async def prompt_generation_node(state: State, config: RunnableConfig) -> Dict:
    """
    Generates a suitable COT prompt to solve the user's question.

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
    system_prompt = Prompts.COT_SEED
    partial_prompt = prompt.partial(system_prompt=system_prompt)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"))
    generate = partial_prompt | llm

    try:
        res = await generate.ainvoke({"messages": state["messages"]})
        # Do not save generated COT prompt in messages
        return {"cot_prompt": res.content}
    except RuntimeError as e:
        logging.error(f"Error in generation_node: {e}")
        return default_state()


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
            ("system", "{system_prompt}"),
            ("human", "Question: {question}\nPlan: {plan}"),  # Formatted message
            MessagesPlaceholder(variable_name="messages")
        ]
    )
    # default is prompt to generate a CoT prompt
    system_prompt = Prompts.GENERATION_SYSTEM_PROMPT
    partial_prompt = prompt.partial(system_prompt=system_prompt)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"))
    generate = partial_prompt | llm

    try:
        question = state["messages"][0]
        plan = state.get("cot_prompt", "")
        # Skip the first message since it is the original user prompt that was
        # used to create the CoT prompt
        messages = state["messages"][1:]
        res = await generate.ainvoke({"question": question, "plan": plan,
                                      "messages": messages})
        return {"messages": [res], "rounds": 1}
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
            "system",
            "You are a critique assistant. Generate critique and recommendations for the user's submission."
            "Provide detailed recommendations appropriate for the task. If no further improvement are "
            "warranted, clearly state it",
            MessagesPlaceholder(variable_name="messages")
        ]
    )

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"))
    reflect = reflection_prompt | llm
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
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and len(msg.tool_calls) > 0:
                translated += [msg]
            elif isinstance(msg, ToolMessage):
                translated += [msg]
            else:
                content = msg.content
                translated += [cls_map[msg.type](content=content)]
    except Exception as e:
        logging.error(f"Error translating messages: {e}")

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
    builder.add_node("prompt_generation", prompt_generation_node)
    builder.add_node("generate", generation_node)
    builder.add_node("reflect", reflection_node)
    builder.add_node("end", end_node)
    builder.add_edge(START, "prompt_generation")
    builder.add_edge("prompt_generation", "generate")
    builder.add_edge("reflect", "generate")
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
            return "end"
        return "reflect"

    builder.add_conditional_edges("generate", should_continue)
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    graph.get_state
    return graph
