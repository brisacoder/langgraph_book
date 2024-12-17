import os
import logging

from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from typing import List

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    BaseMessage,
    ToolMessage,
)
from langchain_core.prompts import ChatPromptTemplate
from models.artist_success import ArtistTimelineResponse
from models.artist_list import ArtistSimilarList
from prompts import Prompts
from langchain_openai import ChatOpenAI


@tool
def find_similar_artists(artists: List[str]) -> ArtistSimilarList:
    """
    Finds similar artists for each artist in the provided list.

    Args:
        artists (List[str]): A list of artist names to find similar artists for.
            Example: ["Taylor Swift", "Eric Clapton"]

    Returns:
        ArtistSimilarList: A structured output containing each artist and their similar artists.

        - `artists`: A list of objects with:
            - `name` (str): The name of the original artist.
            - `similar_artists` (List[dict]): A list of similar artists.
                - `name` (str): The name of a similar artist.

        Example:
        {
            "artists": [
                {
                    "name": "Taylor Swift",
                    "similar_artists": [
                        {"name": "Kacey Musgraves"},
                        {"name": "Carrie Underwood"}
                    ]
                }
            ]
        }
    """

    prompt = ChatPromptTemplate(
        [
            (
                "system",
                "{system_prompt}",
            ),
            ("human", "{human_prompt}"),
        ]
    )
    partial_prompt = prompt.partial(system_prompt=Prompts.SYSTEM)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"), temperature=1.0)
    llm_with_structure = llm.with_structured_output(
        schema=ArtistSimilarList, method="json_schema"
    )
    generate = partial_prompt | llm_with_structure

    try:
        llm_response = generate.invoke(
            {
                "human_prompt": HumanMessage(
                    content=f"Provide 2-3 similar artists to each artists in the list {artists}"
                )
            }
        )
        return llm_response
    except RuntimeError as e:
        logging.error(f"Error in generation_node: {e}")
        return {"messages": []}


@tool
def find_artists_timeline(artists: List[str]) -> ArtistTimelineResponse:
    """
    Determines if each artist in the list achieved mainstream success after 2010.

    Args:
        artists (List[str]): A list of artist names to evaluate.
            Example: ["Taylor Swift", "Eric Clapton"]

    Returns:
        ArtistTimelineResponse: A structured response with:
            - `artists`: List of objects containing:
                - `name` (str): Artist's name.
                - `success_after_2010` (bool): Whether the artist achieved success after 2010.

        Example:
        {
            "artists": [
                {"name": "Taylor Swift", "success_after_2010": True},
                {"name": "Eric Clapton", "success_after_2010": False}
            ]
        }

    Notes:
        Relies on OpenAI LLM with structured output validated by the `ArtistTimelineResponse` schema.
    """
    prompt = ChatPromptTemplate(
        [
            (
                "system",
                "{system_prompt}",
            ),
            ("human", "{human_prompt}"),
        ]
    )
    partial_prompt = prompt.partial(system_prompt=Prompts.SYSTEM)
    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"), temperature=1.0)
    llm_with_structure = llm.with_structured_output(
        schema=ArtistTimelineResponse, method="json_schema"
    )
    generate = partial_prompt | llm_with_structure

    try:
        llm_response = generate.invoke(
            {
                "human_prompt": HumanMessage(
                    content=f"For each artist, determine if they achieved success after 2010: {artists}"
                )
            }
        )
        return llm_response
    except RuntimeError as e:
        logging.error(f"Error in generation_node: {e}")
        return {"messages": []}


def get_search_tools() -> List[BaseTool]:
    return [find_similar_artists, find_artists_timeline]
