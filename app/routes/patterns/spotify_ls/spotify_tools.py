import logging
import os
import spotipy
from langchain_core.tools import tool
from typing import Any, List, Set, Dict

from tenacity import retry, stop_after_attempt, wait_random_exponential
from utils.spotify_client import get_spotify_client, get_spotify_user_authorization
from utils.spotify_apis import get_spotify_uri_from_name
from models.state import State, get_state
from models.spotify_model import Playlist
from spotify_types import SpotifyID


logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",  # Define the format
    handlers=[logging.StreamHandler()],  # Output to the console
)


@tool
def get_playlists() -> List[Playlist]:
    """
    Retrieves all Spotify Playlist IDs. Each playlist includes the Spotify URI and other relevant data

    Returns:
        List[Playlist]: A list of Spotify Playlist IDs
    """
    sp = get_spotify_client()
    playlists: List[Playlist] = []

    try:
        # Fetch the current user's playlists with pagination
        playlists_raw = sp.user_playlists(user=os.getenv("SPOTIFY_USER_ID"), limit=100)
        while playlists_raw:
            for playlist_data in playlists_raw["items"]:
                # Map API data to the Playlist model
                playlist = Playlist(
                    id=playlist_data["id"],
                    name=playlist_data["name"],
                )
                playlists.append(playlist)
            # Check if there is a next page
            if playlists_raw["next"]:
                playlists_raw = sp.next(playlists_raw)
            else:
                break
    except spotipy.SpotifyException as e:
        return [str(e)]

    # Save state
    state: State = get_state()
    state["playlists"] = playlists

    # Serialize the playlists to JSON-serializable dictionaries
    serialized_playlists = [playlist.model_dump() for playlist in playlists]
    return serialized_playlists


@tool
def create_spotify_playlist(name: str, description: str) -> Dict[str, Any]:
    """
    Creates a new playlist on Spotify.

    This function only creates the playlist; it does not add tracks.
    See add_tracks_to_playlist() to add tracks to a existing playlist

    Args:
        name (str): The name of the new playlist.
        description (str): The description of the playlist.

    Returns:
        Dict[str, Any]: Dictionary representing a Playlist
    """

    if description is None:
        description = "Agentic Playlist"

    sp = get_spotify_user_authorization()
    try:
        # Create a new playlist
        new_playlist_data = sp.user_playlist_create(
            user=os.getenv("SPOTIFY_USER_ID"),
            name=name,
            public=True,
            description=description,
        )
        # Map API data to the Playlist model
        new_playlist = Playlist(
            id=new_playlist_data["id"],
            uri=new_playlist_data["uri"],
            name=new_playlist_data["name"],
            description=new_playlist_data.get("description"),
            owner=new_playlist_data["owner"]["display_name"],
            tracks_total=new_playlist_data["tracks"]["total"],
            is_public=new_playlist_data.get("public"),
            collaborative=new_playlist_data.get("collaborative"),
            snapshot_id=new_playlist_data.get("snapshot_id"),
        )
        state: State = get_state()
        state["new_playlist"] = new_playlist
    except spotipy.SpotifyException as e:
        return {"error": str(e)}
    return new_playlist.model_dump()


@tool
def add_tracks_to_playlist(
    playlist_id: SpotifyID, tracks: List[SpotifyID]
) -> Dict[str, Any]:
    """
    Adds tracks to a Spotify playlist in batches of 20.

    Args:
        playlist_id (SpotifyID): Spotify ID of the playlist.
        tracks (List[SpotifyID]): List of Spotify ID tracks.

    Returns:
        Dict[str, Any]: A dictionary indicating success or error.
    """
    sp = get_spotify_client()
    batch_size = 20
    try:
        # Process tracks in batches of 20
        for i in range(0, len(tracks), batch_size):
            batch = tracks[i : i + batch_size]
            sp.playlist_add_items(playlist_id=playlist_id, items=batch)
    except spotipy.SpotifyException as e:
        return {"error": str(e)}
    return {"success": True}


@tool
def filter_artists_by_id(
    playlist_id: SpotifyID, new_artists: List[SpotifyID]
) -> Set[SpotifyID]:
    """
    Checks `new_artists` against an existing Playlist. It returns a set
     of artists that can be used in a new playlist.

    In essense it will perform set operation `new-artists` - `existing-artists`
    Args:
        playlist_id (SpotifyID): Spotify playlist ID in the format <base-62 number>
        new_artists (List[SpotifyID]): List of artists Spotify IDs

    Returns:
        Dict[str, Set[SpotifyID]]: List of artists Spotify IDs that can be used in a new playlist
    """
    state: State = get_state()
    artists: Set[SpotifyID] = set()
    state["candidate_artists"] = set(new_artists)
    for v in state["artists_uris"].keys():
        artists.add(v)
    valid_artists = state["candidate_artists"] - artists
    state["valid_artists"] = valid_artists
    return valid_artists


@tool
def filter_artists_by_name(playlist_id: SpotifyID, new_artists: List[str]) -> List[str]:
    """
    Checks `new_artists` against an existing Playlist. It returns a set
     of artists that can be used in a new playlist.

    Args:
        playlist_id (SpotifyID): Spotify playlist ID in the format <base-62 number>
        new_artists (List[str]): List of artists URIs

    Returns:
        Set[str]: List of artists names that can be used in a new playlist
    """
    state: State = get_state()
    spotify_uris = get_spotify_uri_from_name(new_artists)
    valid_artists: List[str] = []
    for uri in spotify_uris:
        if uri not in state["artists_uri"]:
            valid_artists.append(uri)
    return valid_artists


@tool
def find_top_tracks(artists: List[str]) -> List[str]:
    """
    Find top tracks for each of Spotify artist ID on the list.

    Args:
        artists (List[str]): List of Spotify artists URIs

    Returns:
       List[SpotifyID]: A list of Spotify track URIs.
    """

    tracks: List[SpotifyID] = []
    sp = get_spotify_client()
    for artist in artists:
        try:
            top_tracks = sp.artist_top_tracks(artist, country="US")
            for track in top_tracks["tracks"]:
                tracks.append(track["uri"])
        except Exception as e:
            print(f"Unexpected error for artist {artist}: {str(e)}")
            continue
    return tracks


@tool
def find_top_tracks_by_name(artists: List[str]) -> List[SpotifyID]:
    """
    Find top tracks for each of Spotify artists name on the list.

    Args:
        artists (List[str]): List of Spotify artists IDs in <base-62 number>

    Returns:
       List[SpotifyID]: A list of Spotify track URIs.
    """

    tracks: List[str] = []

    spotify_uris = get_spotify_uri_from_name(artists)

    sp = get_spotify_client()
    for uri in spotify_uris:
        try:
            top_tracks = sp.artist_top_tracks(uri, country="US")
            for track in top_tracks["tracks"]:
                tracks.append(track["uri"])
        except Exception as e:
            print(f"Unexpected error for artist {uri}: {str(e)}")
            continue
    return tracks


@tool
def get_artists_from_playlist(playlist_id: SpotifyID) -> Dict[SpotifyID, str]:
    """
    Get the list of artists from a Spotify playlist

    Args:
        playlist_id (SpotifyID): Spotify playlist ID in base-62 number

    Returns:
        Dict[SpotifyID, str]: A dictionary where keys=SpotifyID name and value=artist name
    """
    sp = get_spotify_client()
    playlist_artists_uri: Dict[SpotifyID, str] = {}
    playlist_artists_name: Dict[str, SpotifyID] = {}

    try:
        # Fetch the playlist's tracks with pagination
        playlist = sp.user_playlist(
            user=os.getenv("SPOTIFY_USER_ID"), playlist_id=playlist_id
        )
        if "tracks" in playlist:
            tracks = playlist["tracks"]
            while tracks:
                for item in tracks["items"]:
                    track_data = item["track"]
                    # Map API data to the Track model
                    for artist in track_data["artists"]:
                        playlist_artists_uri[artist["uri"]] = artist["name"]
                        playlist_artists_name[artist["name"]] = artist["uri"]
                # Check if there is a next page
                if tracks["next"]:
                    # TODO unclear in this case
                    tracks = sp.next(tracks)
                else:
                    break
    except spotipy.SpotifyException as e:
        return {SpotifyID("error"): str(e)}

    # Save state
    state = get_state()
    state["artists_uri"] = playlist_artists_uri
    state["artists_name"] = playlist_artists_name

    # Serialize the tracks to JSON-serializable dictionaries
    return playlist_artists_uri


def get_spotify_tools() -> List:
    return [
        get_playlists,
        create_spotify_playlist,
        add_tracks_to_playlist,
        filter_artists_by_id,
        filter_artists_by_name,
        get_artists_from_playlist,
        find_top_tracks_by_name,
        find_top_tracks,
    ]
