import asyncio
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Annotated, List, Sequence
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict


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
    llm = ChatFireworks(
        model="accounts/fireworks/models/mixtral-8x7b-instruct", max_tokens=32768
    )
    generate = prompt | llm

    for chunk in generate.stream({"messages": [request]}):
        print(chunk.content, end="")
        essay += chunk.content

    return {"messages": [await generate.ainvoke(state["messages"])]}


async def reflection_node(state: State) -> State:
    reflection_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a critique assistant. Generate critique and recommendations for the user's submission."
                " Provide detailed recommendations appropriate for the task",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    llm = ChatFireworks(
        model="accounts/fireworks/models/mixtral-8x7b-instruct", max_tokens=32768
    )    
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
        print(event)
        print("---")

asyncio.run(process_events())