import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth


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
