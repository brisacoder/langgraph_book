import logging
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth
from langchain_core.tools import tool
from typing import Any, List, Set, Dict

from tenacity import retry, stop_after_attempt, wait_random_exponential
from state import State, get_state
from spotify_model import Playlist, Track, Tracks
from spotify_types import SpotifyID


logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",  # Define the format
    handlers=[logging.StreamHandler()],  # Output to the console
)


def get_spotify_user_authorization() -> spotipy.Spotify:
    scopes = "user-library-modify, playlist-modify-private, playlist-modify-public"

    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            scope=scopes,
            client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
            client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI"),
        )
    )

    return sp


def get_spotify_client() -> spotipy.Spotify:
    """
    Initializes and returns a Spotify client with user authentication.

    Returns:
        spotipy.Spotify: An authenticated Spotify client.
    """
    auth_manager = SpotifyClientCredentials(
        client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
        client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET"),
    )
    return spotipy.Spotify(auth_manager=auth_manager)


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
def get_track_list_from_playlist(playlist_id: SpotifyID) -> List[Dict[str, Any]]:
    """
    Retrieves the track list for a specific Spotify playlist.

    Args:
        playlist_id (SpotifyID): Spotify playlist ID in the format <base-62 number>

    Returns:
        List[Dict[str, Any]]: A list of Tracks
    """
    sp = get_spotify_client()
    playlist_tracks: List[Track] = []
    playlist_artists: Set[str] = set()

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
                    track = Track(
                        id=track_data["id"],
                        uri=track_data["uri"],
                        name=track_data["name"],
                        artists=[artist["name"] for artist in track_data["artists"]],
                        album=track_data["album"]["name"],
                        duration_ms=track_data.get("duration_ms"),
                        explicit=track_data.get("explicit"),
                        popularity=track_data.get("popularity"),
                    )
                    playlist_tracks.append(track)
                    [
                        playlist_artists.add(artist["name"])
                        for artist in track_data["artists"]
                    ]
                # Check if there is a next page
                if tracks["next"]:
                    # TODO unclear in this case
                    tracks = sp.next(tracks)
                else:
                    break
    except spotipy.SpotifyException as e:
        return [{"error": str(e)}]

    # Save state
    state = get_state()
    state["tracks"] = playlist_tracks
    state["artists"] = playlist_artists

    # Serialize the tracks to JSON-serializable dictionaries
    serialized_tracks = [track.model_dump() for track in playlist_tracks]
    return serialized_tracks


# @tool
# @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
# def get_audio_features(tracks: List[SpotifyID]):
#     """
#     Get audio features such as acousticness, danceability, energy, instrumentalness, tempo and valence.

#     Args:
#         tracks - a list of Spotify IDs

#     Returns:
#         Dict[str, Any]: Dictionary representing tracks audio features
#     """

#     sp = get_spotify_client()
#     audio_features = sp.audio_features(tracks)
#     return audio_features


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
    Adds tracks to a Spotify playlist.

    Args:
        playlist_id (SpotifyID): Spotify ID of the playlist.
        tracks (List[SpotifyID]): List of Spotify ID tracks

    Returns:
        Dict[str, Any]: A dictionary indicating success or error.
    """
    sp = get_spotify_client()
    try:
        sp.playlist_add_items(playlist_id=playlist_id, items=tracks)
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
    for v in state["artists_id"].keys():
        artists.add(v)
    valid_artists = state["candidate_artists"] - artists
    state["valid_artists"] = valid_artists
    return valid_artists


@tool
def filter_artists_by_name(
    playlist_id: SpotifyID, new_artists: List[str]
) -> Set[str]:
    """
    Checks `new_artists` against an existing Playlist. It returns a set
     of artists that can be used in a new playlist.

    Args:
        playlist_id (SpotifyID): Spotify playlist ID in the format <base-62 number>
        new_artists (List[str]): List of artists names

    Returns:
        Set[str]: List of artists names that can be used in a new playlist
    """
    state: State = get_state()
    valid_artists: Set[str] = set()
    for artist in new_artists:
        if artist not in state["artist_name"]:
            valid_artists.add(artist)
    return valid_artists

# @tool
# def find_similar_artists(artists: List[SpotifyID]) -> Dict[SpotifyID, str]:
#     """
#     Find similar artists for a given a list of Spotify artists IDs.

#     Args:
#         artists (List[SpotifyID]): List of Spotify artists IDs in the format <base-62 number>

#     Returns:
#        Dict[SpotifyID, str]: A dictionary where keys are related artist URI and values are artist names
#     """

#     similar_artists: Dict[SpotifyID, str] = {}
#     sp = get_spotify_user_authorization()
#     for artist in artists:
#         try:
#             temp = sp.artist_related_artists(artist)
#             related_artists = temp["artists"]
#         except Exception as e:
#             logger.error(f"Unexpected error for artist {artist}: {str(e)}")
#             continue
#         for item in related_artists:
#             id = item.get("id")
#             if id and id not in artists:
#                 similar_artists[id] = item.get("name")
#     return similar_artists


@tool
def find_top_tracks(artists: List[SpotifyID]) -> List[SpotifyID]:
    """
    Find top tracks for each of Spotify artists on the list.

    Args:
        artists (List[SpotifyID]): List of Spotify artists IDs in <base-62 number>

    Returns:
       List[SpotifyID]: A list of Spotify track IDs.
    """

    tracks: List[SpotifyID] = []
    sp = get_spotify_client()
    for artist in artists:
        try:
            top_tracks = sp.artist_top_tracks(artist, country="US")
            for track in top_tracks["tracks"]:
                tracks.append(track["id"])
        except Exception as e:
            print(f"Unexpected error for artist {artist}: {str(e)}")
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
    playlist_artists_id: Dict[SpotifyID, str] = {}
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
                        playlist_artists_id[artist["id"]] = artist["name"]
                        playlist_artists_name[artist["name"]] = artist["id"]
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
    state["artists"] = playlist_artists_id
    state["artists_name"] = playlist_artists_name

    # Serialize the tracks to JSON-serializable dictionaries
    return playlist_artists_id


def get_spotify_tools() -> List:
    return [
        get_playlists,
        create_spotify_playlist,
        add_tracks_to_playlist,
        filter_artists_by_id,
        filter_artists_by_name,
        get_artists_from_playlist,
        find_top_tracks,
    ]
