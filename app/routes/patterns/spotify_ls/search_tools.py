from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from typing import List, Dict, Any


@tool
def find_similar_artists(artist: str) -> List[Dict[str, Any]]:
    """
    Searches for artists similar to the specified artist and returns detailed search results.

    Args:
        artist (str): The name of the artist for whom similar artists are to be found.
            Example: "Taylor Swift"

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary contains search
        results with the following keys:
            - `url` (str): The URL of the search result.
            - `content` (str): The main content or summary of the search result, which may
              include a list of similar artists, descriptions, or related details.

    Example Output:
        [
            {
                'url': 'https://www.music-map.com/the+record+company',
                'content': "Music-Map The Record Company People who like The Record Company might also like these artists. The closer two names are, the greater the probability people will like both artists. Click on any name to travel along. The Record Company JJ Grey & Mofro Anderson East The Revivalists Nathaniel Rateliff & The Night Sweats..."
            },
            {
                'url': 'https://www.chosic.com/artist/the-record-company/6vYg01ZFt1nREsUDMDPUYX/',
                'content': "Discover The Record Company genres, songs, music analysis and similar artists on Chosic! Skip to content. Chosic Main Menu..."
            },
            {
                'url': 'https://www.lyrics.com/similar-artists/3040950/The-Record-Company',
                'content': "Lyrics.com results about similar artists. Abbreviations.com Anagrams.net Biographies.net Calculators.net Definitions.net Grammar.com Literature.com..."
            }
        ]
    """
    tool = TavilySearchResults(
        max_results=1,
        include_answer=True,
        include_raw_content=True,
        include_images=True,
        search_depth="advanced",
    )
    return tool.invoke({"query": f"Tell me 2-3 artists similar to {artist}"})


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
