class Prompts:
    SPOTIFY = """
    Create and execute a step-by-step plan with atomic tasks to solve the following problem:

    **Objective:** Build a Spotify playlist with tracks that have the same vibe and genres as my 'New Rock and Blues' playlist, following the rules below.

    **Rules:**

    1. **For each artist in the 'New Rock and Blues' playlist, find 3-4 artists of the similar music style**

    2 .**Remove from the new artist list those that are already present in the 'New Rock and Blues' Playlist**

    3. **Focus on Post-2010 Success:** Only include tracks from artists who achieved success after the year 2010.

    4. **Minimum Number of New Artists:** Include tracks from at least 40 different artists not present in the 'New Rock and Blues' playlist.

    5. **Recommend 3-4 tracks for each new artist.

    6. **Arrange for Smooth Listening Experience:** Organize the tracks to create a smooth listening experience, considering tempo, energy, and mood, using best practices.

    7. **Playlist Length:** Ensure the new playlist contains at least 100 tracks.

    **Instructions:**

    - Follow the rules strictly to meet the objective.
    - Prefer using a tool if available, instead of your Knowledge Base
    - In your responses always state the step you are working on
    - Step(s) should be repeated any number of times to achieve the desired outcome.
    - Do not ask for user confirmation
    """
