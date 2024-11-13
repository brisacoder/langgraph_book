import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from langchain_core.tools import tool
from typing import Any, List, Set, Dict
from state import State, get_state
from spotify_model import Playlist, Track, Tracks
from spotify_uri import SpotifyURI


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
def get_playlists() -> Dict[str, List[Playlist]]:
    """
    Retrieves all Spotify playlists for a user. Each playlist includes the Spotify URI and other relevant data

    Returns:
        Dict[str, List[Playlist]]: A dictionary containing a aingle key `playlists` and a list of Playlist as value.
            Each Playlist includes the Spotify URI and other relevant data
    """
    sp = get_spotify_client()
    playlists: List[Playlist] = []

    try:
        # Fetch the current user's playlists with pagination
        playlists_raw = sp.user_playlists(user=os.getenv("SPOTIFY_USER_ID"), limit=100)
        while playlists_raw:
            for playlist_data in playlists_raw['items']:
                # Map API data to the Playlist model
                playlist = Playlist(
                    id=playlist_data['id'],
                    uri=playlist_data['uri'],
                    name=playlist_data['name'],
                    description=playlist_data.get('description'),
                    owner=playlist_data['owner']['display_name'],
                    tracks_total=playlist_data['tracks']['total'],
                    is_public=playlist_data.get('public'),
                    collaborative=playlist_data.get('collaborative'),
                    snapshot_id=playlist_data.get('snapshot_id')
                )
                playlists.append(playlist)
            # Check if there is a next page
            if playlists_raw['next']:
                playlists_raw = sp.next(playlists_raw)
            else:
                break
    except spotipy.SpotifyException as e:
        return {"error": [str(e)]}

    # Save state
    state: (State) = get_state()
    state["playlists"] = playlists

    # Serialize the playlists to JSON-serializable dictionaries
    serialized_playlists = [playlist.model_dump() for playlist in playlists]
    return {"playlists": serialized_playlists}


@tool
def get_track_list(playlist_id: SpotifyURI) -> Dict[str, List[Track]]:
    """
    Retrieves the track list for a specific Spotify playlist.

    Args:
        playlist_id (SpotifyURI): Spotify playlist URI in the format spotify:playlist:<base-62 number>

    Returns:
        Dict[str, List[Track]]: A dictionary containing a list of Track models under the 'tracks' key.
    """
    sp = get_spotify_client()
    playlist_tracks: List[Track] = []
    playlist_artists: Set[str] = set()

    try:
        # Fetch the playlist's tracks with pagination
        playlist = sp.user_playlist(user=os.getenv("SPOTIFY_USER_ID"), playlist_id=playlist_id)
        if 'tracks' in playlist:
            tracks = playlist["tracks"]
            while tracks:
                for item in tracks['items']:
                    track_data = item['track']
                    # Map API data to the Track model
                    track = Track(
                        id=track_data['id'],
                        uri=track_data['uri'],
                        name=track_data['name'],
                        artists=[artist['name'] for artist in track_data['artists']],
                        album=track_data['album']['name'],
                        duration_ms=track_data.get('duration_ms'),
                        explicit=track_data.get('explicit'),
                        popularity=track_data.get('popularity')
                    )
                    playlist_tracks.append(track)
                    [playlist_artists.add(artist['name']) for artist in track_data['artists']]
                # Check if there is a next page
                if tracks['next']:
                    # TODO unclear in this case
                    tracks = sp.next(tracks)
                else:
                    break
    except spotipy.SpotifyException as e:
        return {"error": [str(e)]}

    # Save state
    state = get_state()
    state["tracks"] = playlist_tracks
    state["artists"] = playlist_artists

    # Serialize the tracks to JSON-serializable dictionaries
    serialized_tracks = [track.model_dump() for track in playlist_tracks]
    return {"tracks": serialized_tracks}


@tool
def create_spotify_playlist(name: str, description: str) -> Dict[str, Playlist]:
    """
    Creates a new playlist on Spotify.

    This function only creates the playlist; it does not add tracks.
    See tool add_tracks_to_playlist() to add tracks to a existing playlist

    Args:
        name (str): The name of the new playlist.
        description (str): The description of the playlist.

    Returns:
        Dict[str, Playlist]: A dictionary containing the new Playlist model under the 'new_playlist' key.
    """

    if description is None:
        description = "Agentic Playlist"

    sp = get_spotify_client()
    try:
        # Create a new playlist
        new_playlist_data = sp.user_playlist_create(
            user=os.getenv("SPOTIFY_USER_ID"),
            name=name,
            public=True,
            description=description
        )
        # Map API data to the Playlist model
        new_playlist = Playlist(
            id=new_playlist_data['id'],
            uri=new_playlist_data['uri'],
            name=new_playlist_data['name'],
            description=new_playlist_data.get('description'),
            owner=new_playlist_data['owner']['display_name'],
            tracks_total=new_playlist_data['tracks']['total'],
            is_public=new_playlist_data.get('public'),
            collaborative=new_playlist_data.get('collaborative'),
            snapshot_id=new_playlist_data.get('snapshot_id')
        )
        state: State = get_state()
        state["new_playlist"] = new_playlist
    except spotipy.SpotifyException as e:
        return {"error": str(e)}
    return {"new_playlist": new_playlist.model_dump()}


@tool
def add_tracks_to_playlist(playlist_id: str, tracks: Tracks) -> Dict[str, Any]:
    """
    Adds tracks to a Spotify playlist.

    Args:
        playlist_id (str): ID of the playlist.
        tracks (Tracks): Spotify Pydantic Model of a List of tracks

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
def filter_artists(playlist_id: str, new_artists: List[str]) -> Dict[str, List[str]]:
    """
    Checks `new-artists` against an existing Playlist. It returns a set 
    of artists that can be used in a new playlist. 

    In essense it will perform set operation `new-artists` - `existing-artists`
    Args:
        playlist_id (SpotifyURI): Spotify playlist URI in the format spotify:playlist:<base-62 number>
        new_artists (List[str]): A list of potential artist names

    Returns:
        Dict[str, Set[str]]: Artists that can be used in a new playlist
    """
    state: State = get_state()
    state['candidate_artists'] = set(new_artists)
    valid_artists = state['candidate_artists'] - state["artists"]
    state["valid_artists"] = valid_artists
    return {"valid_artists": valid_artists}


@tool
def find_similar_artists(artists: List[SpotifyURI]) -> Set[SpotifyURI]:
    """
    Find similar artists for a given a list of Spotify artists URIs. It returns a Set of SpotifyURIs. 

    Args:
        artists (List[SpotifyURI]): List of Spotify artists URIs in the format spotify:artist:<base-62 number>

    Returns:
       Set[Dict]: A set of Spotify URIs.
    """

    similar_artists: Set[SpotifyURI] = set()
    sp = get_spotify_client()
    for artist in artists:
        for item in sp.artist_related_artists(artist)["artists"]:
            uri = item["uri"]
            if uri not in artists:
                similar_artists.add(item["uri"])
    return similar_artists


@tool
def get_artists_from_playlist(playlist_id: SpotifyURI) -> Dict[str, Dict[str, SpotifyURI]]:
    """
    Get the list of unique artists from a Spotify playlist URI

    Args:
        playlist_id (SpotifyURI): Spotify playlist URI in the format spotify:playlist:<base-62 number>

    Returns:
        Dict[str, SpotifyURI]: A dictionary where keys=artist name and value=URI
    """
    sp = get_spotify_client()
    playlist_artists: Dict[str, SpotifyURI] = {}

    try:
        # Fetch the playlist's tracks with pagination
        playlist = sp.user_playlist(user=os.getenv("SPOTIFY_USER_ID"), playlist_id=playlist_id)
        if 'tracks' in playlist:
            tracks = playlist["tracks"]
            while tracks:
                for item in tracks['items']:
                    track_data = item['track']
                    # Map API data to the Track model
                    for artist in track_data['artists']:
                        playlist_artists[artist['name']] = artist["uri"]
                # Check if there is a next page
                if tracks['next']:
                    # TODO unclear in this case
                    tracks = sp.next(tracks)
                else:
                    break
    except spotipy.SpotifyException as e:
        return {"artists": {"error": str(e)}}

    # Save state
    state = get_state()
    state["artists"] = playlist_artists

    # Serialize the tracks to JSON-serializable dictionaries
    return {"artists": playlist_artists}
