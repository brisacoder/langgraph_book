import json
import os
from typing import List

import spotipy

from spotify_client import get_spotify_client


CACHE_FILE = "spotify_name_uri_cache.json"


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_spotify_uri_from_name(names: List[str]) -> List[str]:
    """
    Get the Spotify URI for each artist name, using a JSON-based cache to
    avoid repeated API calls across runs.

    Args:
        names (List[str]): A list of artist names

    Returns:
        List[str]: A list of Spotify URIs
    """

    cache = load_cache()
    sp = get_spotify_client()
    spotify_uris: List[str] = []

    # Determine which names need fetching
    names_to_fetch = [name for name in names if name not in cache]

    # Fetch missing names from Spotify API
    for name in names_to_fetch:
        try:
            spotify_data = sp.search(q=name, limit=1, type="artist")
            items = spotify_data.get("artists", {}).get("items", [])
            if items and "uri" in items[0]:
                cache[name] = items[0]["uri"]
            else:
                # If no URI was found, store None
                cache[name] = None
        except spotipy.SpotifyException as e:
            print(f"Unexpected error for artist '{name}': {str(e)}")
            # Store None to avoid repeated failing lookups
            cache[name] = None

    # Save the updated cache to disk
    save_cache(cache)

    # Prepare the final list of spotify URIs
    for name in names:
        artist_uri = cache.get(name)
        if artist_uri is not None:
            spotify_uris.append(artist_uri)

    return spotify_uris
