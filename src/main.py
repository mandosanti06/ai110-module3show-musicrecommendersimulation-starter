"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender. It runs the
recommender against a suite of "taste profiles" — three ordinary ones plus
three adversarial / edge-case ones designed to stress the scoring logic and
surface where it can be tricked or behave unexpectedly.

The functions being exercised live in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

# Support both `python -m src.main` (package import) and `python src/main.py`.
try:
    from src.recommender import (
        load_songs,
        recommend_songs,
        detect_conflicts,
        profile_is_empty,
    )
except ModuleNotFoundError:
    from recommender import (
        load_songs,
        recommend_songs,
        detect_conflicts,
        profile_is_empty,
    )


# ---------------------------------------------------------------------------
# Taste profiles
# ---------------------------------------------------------------------------
# Each entry is (label, note, user_prefs). The note explains what the profile
# is probing for — especially the adversarial ones, where the point is to see
# whether the scoring recipe can be "tricked" into an odd ranking.

PROFILES = [
    # --- Three distinct, well-formed profiles ---------------------------------
    (
        "High-Energy Pop",
        "A textbook profile — everything points the same direction.",
        {"genre": "pop", "mood": "happy", "energy": 0.9, "likes_acoustic": False},
    ),
    (
        "Chill Lofi",
        "Low energy, acoustic-loving study listener.",
        {"genre": "lofi", "mood": "chill", "energy": 0.30, "likes_acoustic": True},
    ),
    (
        "Deep Intense Rock",
        "High energy, produced (non-acoustic) heavy listener.",
        {"genre": "rock", "mood": "intense", "energy": 0.95, "likes_acoustic": False},
    ),

    # --- Three adversarial / edge-case profiles -------------------------------
    (
        "ADVERSARIAL · Conflicting Energy vs Mood",
        "Wants 'sad' mood but 0.9 energy — and 'likes_acoustic' while asking for "
        "metal (metal is the least acoustic genre). Every signal fights another.",
        {"genre": "metal", "mood": "sad", "energy": 0.9, "likes_acoustic": True},
    ),
    (
        "EDGE CASE · Empty Profile",
        "User stated no preferences at all. No scoring rule can fire, so the "
        "ranking collapses onto the tie-breakers (danceability, then id).",
        {},
    ),
    (
        "EDGE CASE · Out-of-Range Energy",
        "energy = 2.0 is outside the valid 0–1 range. The graded energy term "
        "goes NEGATIVE, so this profile can actively push songs down the list.",
        {"genre": "pop", "mood": "happy", "energy": 2.0, "likes_acoustic": False},
    ),
]


def print_recommendations(label: str, note: str, user_prefs: dict, songs: list) -> None:
    """Rank the catalog for one profile and print its top 5 with reasons."""
    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("#" * 70)
    print(f"# PROFILE: {label}")
    print(f"# {note}")
    print(f"# prefs = {user_prefs}")
    print("#" * 70)

    # Validation layer: name any problem with the profile before showing
    # results, so a nonsense or contentless ranking is never presented as a
    # clean match. (Fixes the "silent contradiction" and "hidden default".)
    if profile_is_empty(user_prefs):
        print(
            "\n⚠ EMPTY PROFILE: no genre/mood/energy/acoustic preference given.\n"
            "  Nothing to match on — results below are ordered by danceability\n"
            "  only, NOT by how well they fit you."
        )
    for warning in detect_conflicts(user_prefs):
        print(f"\n⚠ CONFLICT: {warning}")

    print(f"\nTop {len(recommendations)} recommendations\n")
    print("=" * 60)
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"{rank}. {song['title']} — {song['artist']}")
        print(f"   Score: {score:.2f}")
        print("   Reasons:")
        for reason in explanation.split("; "):
            print(f"     • {reason}")
        print("=" * 60)
    print()


def main() -> None:
    """Load the catalog once, then rank it for every profile in PROFILES."""
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    for label, note, user_prefs in PROFILES:
        print_recommendations(label, note, user_prefs, songs)


if __name__ == "__main__":
    main()
