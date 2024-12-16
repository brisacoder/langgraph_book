from collections import defaultdict
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from typing import List, Dict, Any


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
    search_result = {}
    tool = TavilySearchResults(
        max_results=1,
        include_answer=True,
        include_raw_content=True,
        include_images=True,
        search_depth="advanced",
    )
    for artist in artists:
        search_result[artist] = tool.invoke(
            {"query": f"Tell me 2-3 artists similar to {artist}"}
        )

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

    return [find_similar_artists]
