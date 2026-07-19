"""
Command line runner for the Music Recommender Simulation.

This script showcases the four challenge features:
  1. Advanced song attributes (popularity, decade, mood tags, language, …)
  2. Multiple scoring modes via a Strategy pattern (switchable below)
  3. A diversity penalty that avoids repeating artists / genres in the top 5
  4. A formatted results table (tabulate, with an ASCII fallback)

The logic lives in recommender.py:
- load_songs / score_song / recommend_songs
- STRATEGIES (the switchable scoring modes)
"""

# Support both `python -m src.main` (package import) and `python src/main.py`.
try:
    from src.recommender import (
        load_songs,
        recommend_songs,
        detect_conflicts,
        profile_is_empty,
        STRATEGIES,
        get_strategy,
    )
except ModuleNotFoundError:
    from recommender import (
        load_songs,
        recommend_songs,
        detect_conflicts,
        profile_is_empty,
        STRATEGIES,
        get_strategy,
    )

# tabulate makes a nicer table, but we degrade gracefully to plain ASCII so the
# script runs even if the dependency isn't installed.
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


# ---------------------------------------------------------------------------
# Table rendering (Challenge 4)
# ---------------------------------------------------------------------------

def format_table(recommendations) -> str:
    """Render recommendations as a table that INCLUDES the reasons per song."""
    headers = ["#", "Title", "Artist", "Genre", "Score", "Why it was picked"]
    rows = []
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        reasons = "\n".join(f"• {r}" for r in explanation.split("; "))
        rows.append([rank, song["title"], song["artist"], song["genre"],
                     f"{score:.2f}", reasons])

    if HAS_TABULATE:
        return tabulate(rows, headers=headers, tablefmt="grid")
    return _ascii_table(headers, rows)


def _ascii_table(headers, rows) -> str:
    """Fallback table when tabulate isn't installed. Reasons go below each row."""
    line = "-" * 74
    out = [line,
           f"{'#':<3} {'Title':<22} {'Artist':<20} {'Genre':<12} {'Score':>6}",
           line]
    for rank, title, artist, genre, score, reasons in rows:
        out.append(f"{rank:<3} {title[:22]:<22} {artist[:20]:<20} {genre[:12]:<12} {score:>6}")
        for reason_line in reasons.split("\n"):
            out.append(f"      {reason_line}")
        out.append(line)
    return "\n".join(out)


def show(title: str, note: str, recommendations) -> None:
    """Print a titled block with a table of recommendations."""
    print("═" * 74)
    print(title)
    if note:
        print(note)
    print("═" * 74)
    print(format_table(recommendations))
    print()


# ---------------------------------------------------------------------------
# Demo profiles
# ---------------------------------------------------------------------------

# A rich profile that exercises the advanced features (Challenge 1). Genre and
# mood deliberately point at DIFFERENT songs (funk vs euphoric) so the scoring
# modes in Challenge 2 visibly disagree about the #1 pick.
RICH_PROFILE = {
    "genre": "funk",
    "mood": "euphoric",
    "energy": 0.85,
    "likes_acoustic": False,
    "decade": 2000,
    "mood_tags": ["party", "euphoric", "groovy"],
    "language": "english",
    "prefers_popular": True,
    "allow_explicit": False,
}

# A profile that naturally produces repeats (lots of lofi / repeated artists),
# used to show the diversity penalty (Challenge 3).
REPEAT_PRONE_PROFILE = {
    "genre": "lofi",
    "mood": "chill",
    "energy": 0.35,
    "likes_acoustic": True,
}


# ---------------------------------------------------------------------------
# Stress test (kept from the base project so the README's documented output
# stays reproducible with `python -m src.main`).
# ---------------------------------------------------------------------------

STRESS_PROFILES = [
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


def run_stress_test(songs) -> None:
    """Print the six-profile stress test in the block format the README shows."""
    for label, note, user_prefs in STRESS_PROFILES:
        print_recommendations(label, note, user_prefs, songs)


def demo_advanced_features(songs) -> None:
    """Challenge 1: show the new attributes actually moving the ranking."""
    print("\n" + "#" * 74)
    print("# CHALLENGE 1 — Advanced song features in action")
    print("#" * 74)
    recs = recommend_songs(RICH_PROFILE, songs, k=5)
    show(
        "Rich profile: K-pop · energetic · 2020s · party/euphoric · Korean · popular · no explicit",
        "Notice the reasons now include decade, mood-tag, language and popularity points.",
        recs,
    )


def demo_scoring_modes(songs) -> None:
    """Challenge 2: run ONE profile through every scoring mode and compare."""
    print("\n" + "#" * 74)
    print("# CHALLENGE 2 — Switchable scoring modes (Strategy pattern)")
    print("#" * 74)
    for key, strategy in STRATEGIES.items():
        recs = recommend_songs(RICH_PROFILE, songs, k=5, strategy=strategy)
        show(f"Mode: {strategy.name}  (--mode {key})", strategy.description, recs)


def demo_diversity(songs) -> None:
    """Challenge 3: compare the same profile with the penalty off vs on."""
    print("\n" + "#" * 74)
    print("# CHALLENGE 3 — Diversity penalty (avoid repeated artists / genres)")
    print("#" * 74)
    off = recommend_songs(REPEAT_PRONE_PROFILE, songs, k=5, diversity=False)
    show("Diversity OFF — lofi profile", "Watch the repeated genre/artist stack up.", off)
    on = recommend_songs(REPEAT_PRONE_PROFILE, songs, k=5, diversity=True)
    show("Diversity ON — same profile", "Repeats get penalized so the list spreads out.", on)


def main() -> None:
    """Load the catalog once, then run the stress test and the four challenge demos."""
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    # Base-project stress test (keeps the README's documented output valid).
    run_stress_test(songs)

    # Stretch-challenge showcase.
    print("Table renderer:", "tabulate" if HAS_TABULATE else "ASCII fallback")
    print(f"Available scoring modes: {', '.join(STRATEGIES)}")
    for warning in detect_conflicts(RICH_PROFILE):
        print(f"⚠ CONFLICT: {warning}")

    demo_advanced_features(songs)
    demo_scoring_modes(songs)
    demo_diversity(songs)


if __name__ == "__main__":
    main()
