from pydantic import BaseModel, Field
from typing import List


class ArtistSuccess(BaseModel):
    """
    Represents an artist and whether they achieved mainstream success after 2010.
    """

    name: str = Field(..., description="The name of the artist.")
    success_after_2010: bool = Field(
        ...,
        description="Indicates whether the artist achieved mainstream success after 2010.",
    )


class ArtistTimelineResponse(BaseModel):
    """
    Represents the response for determining the success timeline of artists.

    This model contains a list of artists and their success status.
    """

    artists: List[ArtistSuccess] = Field(
        ..., description="A list of artists with their names and success status."
    )