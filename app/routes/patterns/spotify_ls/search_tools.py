import os
import logging

from collections import defaultdict
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from typing import List, Dict, Any

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    BaseMessage,
    ToolMessage,
)
from langchain_core.prompts import ChatPromptTemplate
from prompts import Prompts
from langchain_openai import ChatOpenAI


@tool
def find_similar_artists(artists: List[str]) -> Dict[str, List[Any]]:
    """
    Searches for artists similar to the specified artist and returns detailed search results.

    Args:
        artist (List[str]): The names of the artists for whom similar artists are to be found.
            Example: ["Taylor Swift", "Eric Clapton"]

    Returns:
        Dict[str, List[Any]]: A dictionaries, where each key is the name of an artist the value contains
        a list of the search results with the following keys:
            - `url` (str): The URL of the search result.
            - `content` (str): The main content or summary of the search result, which may
              include a list of similar artists, descriptions, or related details.

    """
    prompt = ChatPromptTemplate(
        [
            (
                "system",
                "{system_prompt}",
            ),
        ]
    )
    partial_prompt = prompt.partial(system_prompt=Prompts.SYSTEM)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"), temperature=1.0)
    llm_with_structure = llm.with_structured_output(
        schema=Plan, method="json_schema", include_raw=True
    )
    generate = partial_prompt | llm_with_structure

    try:
        llm_response = generate.invoke({"messages": state["messages"]})
        return {"messages": llm_response["raw"], "plan": llm_response["parsed"]}
    except RuntimeError as e:
        logging.error(f"Error in generation_node: {e}")
        return {"messages": []}


@tool
def find_artists_timeline(artists: List[str]) -> Dict[str, List[Any]]:
    """
    Determines the year when an artist became mainsteam.

    Args:
        artist (List[str]): The names of the artists for whom similar artists are to be found.
            Example: ["Taylor Swift", "Eric Clapton"]

    Returns:
        Dict[str, List[Any]]: A dictionaries, where each key is the name of an artist the value contains
        a list of the search results with the following keys:
            - `url` (str): The URL of the search result.
            - `content` (str): The main content or summary of the search result, which may
              include a list of similar artists, descriptions, or related details.

    """
    search_result = {}
    tool = TavilySearchResults(
        max_results=1,
        include_answer=True,
        include_raw_content=True,
        search_depth="advanced",
    )

    for artist in artists:
        try:
            search_result[artist] = tool.invoke(
                {"query": f"Which year the artist {artist} became mainstream?"}
            )
        except Exception as e:
            print(f"Unexpected error for artist {artist}: {str(e)}")
    return search_result


def get_search_tools() -> List[BaseTool]:
    # search_tool = TavilySearchResults(
    #     max_results=5,
    #     include_answer=True,
    #     include_raw_content=True,
    #     include_images=True,
    #     # search_depth="advanced",
    #     # include_domains = []
    #     # exclude_domains = []
    # )

    return [find_similar_artists, find_artists_timeline]
