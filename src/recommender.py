import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

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

def _profile_to_prefs(user: UserProfile) -> Dict:
    """Bridge the UserProfile dataclass to the dict shape score_song expects."""
    return {
        "genre": user.favorite_genre,
        "mood": user.favorite_mood,
        "energy": user.target_energy,
        "likes_acoustic": user.likes_acoustic,
    }


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py

    This is a thin object-oriented wrapper around the functional core
    (score_song / recommend_songs) so the class and the CLI share ONE
    implementation instead of drifting apart. Song / UserProfile dataclasses
    are converted to the plain dicts the scoring functions operate on.
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Score every song for this user and return the top k, best first.

        Ties break on higher danceability, then lower id — identical to
        recommend_songs() so both entry points rank the catalog the same way.
        """
        prefs = _profile_to_prefs(user)
        scored = [(song, score_song(prefs, asdict(song))[0]) for song in self.songs]
        scored.sort(key=lambda item: (-item[1], -item[0].danceability, item[0].id))
        return [song for song, _score in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return the plain-English reasons this song earned its score."""
        prefs = _profile_to_prefs(user)
        _score, reasons = score_song(prefs, asdict(song))
        return "; ".join(reasons) if reasons else "no strong matches"

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

# The normalized audio features (energy, valence, danceability, acousticness)
# all live on a 0.0–1.0 scale. Preferences are validated against this range so
# a malformed input can't push the score outside its designed bounds.
FEATURE_MIN, FEATURE_MAX = 0.0, 1.0

# The four keys score_song actually reads. Used to tell a real profile apart
# from an empty / all-unknown one (which otherwise ranks silently by danceability).
PREFERENCE_KEYS = ("genre", "mood", "energy", "likes_acoustic")

# Moods that, in this catalog, describe inherently low- or high-energy songs.
# Used only to *warn* about self-contradictory profiles — the user is still
# free to ask for them, they just get told the request fights itself.
LOW_ENERGY_MOODS = {"sad", "melancholic", "relaxed", "chill", "dreamy"}
HIGH_ENERGY_MOODS = {"intense", "energetic", "euphoric", "confident", "dark"}

# Genres that are almost never acoustic; pairing them with likes_acoustic=True
# is a contradiction worth surfacing.
RARELY_ACOUSTIC_GENRES = {"metal", "electronic", "edm", "synthwave", "techno"}


def _clamp(value: float, low: float = FEATURE_MIN, high: float = FEATURE_MAX) -> float:
    """Constrain a value to [low, high]. Guards the math against bad input."""
    return max(low, min(high, value))


def profile_is_empty(user_prefs: Dict) -> bool:
    """True when the profile carries no signal score_song can act on.

    Such a profile isn't wrong, but every scoring rule stays silent and the
    ranking collapses onto the danceability tie-breaker. Callers can use this
    to say so out loud instead of presenting a danceability chart as a "match".
    """
    return not any(key in user_prefs for key in PREFERENCE_KEYS)


def detect_conflicts(user_prefs: Dict) -> List[str]:
    """Return plain-English warnings for self-contradictory / invalid prefs.

    This is the fix for the "silently averages a contradiction" limitation:
    the recommender still answers, but it names the conflict so a nonsense
    ranking is never presented as if it cleanly matched the request.
    """
    warnings: List[str] = []
    energy = user_prefs.get("energy")
    mood = user_prefs.get("mood")
    genre = user_prefs.get("genre")

    # 1) Out-of-range energy. score_song clamps it; announce that it did.
    if energy is not None and not (FEATURE_MIN <= energy <= FEATURE_MAX):
        warnings.append(
            f"energy {energy} is outside 0.0–1.0 and was clamped to {_clamp(energy):.1f}"
        )

    # 2) Energy vs mood pulling in opposite directions.
    if energy is not None and mood is not None:
        if mood in LOW_ENERGY_MOODS and energy >= 0.66:
            warnings.append(
                f"mood '{mood}' is typically low-energy, but target energy is {energy}"
            )
        elif mood in HIGH_ENERGY_MOODS and energy <= 0.34:
            warnings.append(
                f"mood '{mood}' is typically high-energy, but target energy is {energy}"
            )

    # 3) Wanting acoustic songs from a genre that almost never is one.
    if user_prefs.get("likes_acoustic") and genre in RARELY_ACOUSTIC_GENRES:
        warnings.append(
            f"likes_acoustic is set, but genre '{genre}' is rarely acoustic"
        )

    return warnings


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
    # The target is clamped to [0, 1] and `closeness` is clamped to [0, 1] so a
    # malformed input (e.g. energy=2.0) can never make this term go NEGATIVE or
    # exceed its designed 0.0–2.0 range — it degrades to "no energy bonus".
    target_energy = user_prefs.get("energy")
    if target_energy is not None and song.get("energy") is not None:
        safe_target = _clamp(target_energy)
        closeness = _clamp(1.0 - abs(song["energy"] - safe_target))
        energy_points = 2.0 * closeness
        score += energy_points
        reasons.append(
            f"energy fit: {song['energy']} vs target {safe_target} "
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
