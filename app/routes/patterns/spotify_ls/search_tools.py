from typing import Any, List
from langchain_community.tools.tavily_search import TavilySearchResults


def get_search_tools() -> List[Any]:
    search_tool = TavilySearchResults(
        max_results=5,
        include_answer=True,
        include_raw_content=True,
        include_images=True,
        # search_depth="advanced",
        # include_domains = []
        # exclude_domains = []
    )

    return [search_tool]
