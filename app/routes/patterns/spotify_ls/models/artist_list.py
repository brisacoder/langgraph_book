from pydantic import BaseModel, Field
from typing import List


class SimilarArtist(BaseModel):
    """
    Represents an artist similar to the original artist.
    """

    name: str = Field(..., description="The name of a similar artist.")


class ArtistWithSimilar(BaseModel):
    """
    Represents an artist and their list of similar artists.
    """

    name: str = Field(
        ...,
        description="The name of the original artist.",
    )
    similar_artists: List[SimilarArtist] = Field(
        ..., description="A list of artists similar to the original artist."
    )


class ArtistSimilarList(BaseModel):
    """
    Represents a collection of artists, each with their list of similar artists.

    This model is designed for structured output where each artist
    is paired with a curated list of similar artists.
    """

    artists: List[ArtistWithSimilar] = Field(
        ..., description="A list of artists and their respective similar artists."
    )
