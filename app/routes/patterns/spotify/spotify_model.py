from typing import List, Optional
from pydantic import BaseModel, Field


# # Define a Pydantic model for Playlist
# class Playlist(BaseModel):
#     """
#     A model representing a Spotify playlist.
#     """
#     id: str = Field(..., description="The unique identifier for the playlist.")
#     uri: str = Field(..., description="The Spotify URI for the playlist.")
#     name: str = Field(..., description="The name of the playlist.")
#     description: Optional[str] = Field(description="The playlist's description.")
#     owner: Optional[str] = Field(description="The display name of the playlist's owner.")
#     tracks_total: Optional[int] = Field(description="The total number of tracks in the playlist.")
#     is_public: Optional[bool] = Field(description="Indicates if the playlist is public.")
#     collaborative: Optional[bool] = Field(description="Indicates if the playlist is collaborative.")
#     snapshot_id: Optional[str] = Field(description="The version identifier for the current playlist.")


class Playlist(BaseModel):
    """
    A model representing a Spotify playlist.
    """
    uri: str = Field(..., description="The Spotify URI for the playlist.")
    name: str = Field(..., description="The name of the playlist.")


# Define a Pydantic model for Track
class Track(BaseModel):
    """
    A model representing a Spotify track.
    """
    id: str = Field(..., description="The unique identifier for the track.")
    uri: str = Field(..., description="The Spotify URI for the track.")
    name: str = Field(..., description="The name of the track.")
    artists: List[str] = Field(..., description="A list of artists who performed the track.")
    album: str = Field(..., description="The name of the album the track is from.")
    duration_ms: Optional[int] = Field(description="The track length in milliseconds.")
    explicit: Optional[bool] = Field(description="Indicates if the track has explicit content.")
    popularity: Optional[int] = Field(description="The popularity of the track (0-100).")


# Define a Pydantic model for Tracks
class Tracks(BaseModel):
    """
    A model representing a collection of Spotify tracks.
    """
    tracks: List[Track] = Field(..., description="A list of Track objects.")
    total: Optional[int] = Field(description="Total number of tracks in the collection.")
    playlist_name: Optional[str] = Field(description="Name of the playlist.")

    class Config:
        """
        Configuration for the Tracks model.
        """
        str_strip_whitespace = True
