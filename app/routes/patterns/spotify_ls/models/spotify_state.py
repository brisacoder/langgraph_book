import operator
from typing import List, Annotated, Set, Dict
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from plan import Plan
from spotify_model import Playlist, Track
from models.spotify_types import SpotifyURI


class SpotifyState(TypedDict, total=False):
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
    artists_uri: Dict[SpotifyURI, str]
    artists_name: Dict[str, SpotifyURI]


spotify_state: SpotifyState = SpotifyState()


def get_spotify_state():
    return spotify_state
