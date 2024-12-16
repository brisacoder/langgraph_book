import operator
from typing import List, Annotated, Set, Dict
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from plan import Plan
from spotify_model import Playlist, Track
from spotify_types import SpotifyID


class State(TypedDict, total=False):
    """
    Represents the state of the conversation and Spotify information

    Attributes:
        playlists (List[Playlist]): A list of Spotify Playlists.
        tracks (List[Track]): Track list for a Spotify Playlist
        new_playlist: (Playlist) : New Spotify playlist data
        new_tracks: (List[Track]): Tracks for the new playlist
    """

    new_playlist: Playlist
    new_tracks: List[Track]
    valid_artists: Set[str]
    candidate_artists: Set[str]
    playlists: List[Playlist]
    tracks: List[Track]
    artists: Dict[SpotifyID, str]
    messages: Annotated[List[BaseMessage], add_messages]
    spotify_prompt: str
    plan: Plan
    rounds: Annotated[int, operator.add]


state: State = State()


def get_state():
    return state
