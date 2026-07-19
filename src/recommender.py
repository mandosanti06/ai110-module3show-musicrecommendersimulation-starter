import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """Read the CSV catalog into a list of song dicts, with numeric fields typed."""
    # Columns that should be stored as integers vs. floats so we can do
    # math on them later. Everything else stays a string.
    int_fields = {"id", "tempo_bpm"}
    float_fields = {"energy", "valence", "danceability", "acousticness"}

    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            song: Dict = {}
            for key, value in row.items():
                if key in int_fields:
                    song[key] = int(value)
                elif key in float_fields:
                    song[key] = float(value)
                else:
                    song[key] = value
            songs.append(song)

    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score one song against the user's taste and return (score, reasons).

    Implements the "VibeMatch" recipe from the README: every song starts at
    0 points and earns points for each way it matches the user's taste. Each
    rule that fires also appends a plain-English reason, so every score arrives
    with its receipt.
    """
    score = 0.0
    reasons: List[str] = []

    # Rule 1 — Genre match (+3.0). The strongest single signal of taste.
    if song.get("genre") == user_prefs.get("genre"):
        score += 3.0
        reasons.append(f"genre match: {song['genre']} (+3.0)")

    # Rule 2 — Mood match (+2.0).
    if song.get("mood") == user_prefs.get("mood"):
        score += 2.0
        reasons.append(f"mood match: {song['mood']} (+2.0)")

    # Rule 3 — Energy fit (graded): +2.0 x (1 - |energy - target_energy|).
    # A near-perfect energy match earns almost the full 2.0; a far-off one
    # earns almost nothing, keeping the ranking meaningful instead of clumped.
    target_energy = user_prefs.get("energy")
    if target_energy is not None and song.get("energy") is not None:
        closeness = 1.0 - abs(song["energy"] - target_energy)
        energy_points = 2.0 * closeness
        score += energy_points
        reasons.append(
            f"energy fit: {song['energy']} vs target {target_energy} "
            f"({energy_points:+.2f})"
        )

    # Rule 4 — Acoustic fit (+1.0). Only evaluated if the user stated a
    # preference. Rewards acoustic songs for acoustic lovers, and produced
    # songs for everyone else.
    if "likes_acoustic" in user_prefs:
        likes_acoustic = user_prefs["likes_acoustic"]
        acousticness = song.get("acousticness")
        if acousticness is not None:
            if likes_acoustic and acousticness >= 0.6:
                score += 1.0
                reasons.append(f"acoustic fit: acousticness {acousticness} (+1.0)")
            elif not likes_acoustic and acousticness <= 0.3:
                score += 1.0
                reasons.append(f"produced fit: acousticness {acousticness} (+1.0)")

    # Rule 5 — Danceability bonus (+0.5). A gentle tie-breaker.
    if song.get("danceability", 0.0) >= 0.7:
        score += 0.5
        reasons.append(f"danceable: {song['danceability']} (+0.5)")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score every song and return the top k as (song, score, explanation), best first.

    Recommending is just ranking: score every song with score_song(), then
    sort highest-first (tie-break on higher danceability, then lower id) and
    return the top k. Each result carries a plain-English explanation built
    from the reasons that fired.
    """
    # Judge every song in the catalog, pairing it with its score + reasons.
    scored = [(song, *score_song(user_prefs, song)) for song in songs]

    # Sort highest score first; break ties on danceability, then id (both
    # deterministic). Negate the "higher is better" keys for a plain sort.
    scored.sort(
        key=lambda item: (-item[1], -item[0].get("danceability", 0.0), item[0].get("id", 0))
    )

    # Turn each song's reasons into a single explanation string and keep top k.
    return [
        (song, score, "; ".join(reasons) if reasons else "no strong matches")
        for song, score, reasons in scored[:k]
    ]
