from typing import List, Annotated, Set
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from spotify_model import Playlist, Track


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
    artists: Set[str]
    messages: Annotated[List[BaseMessage], add_messages]


state: State = State()


def get_state():
    return state
