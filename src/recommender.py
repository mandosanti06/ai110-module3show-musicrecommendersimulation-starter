import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field, asdict

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py

    The first block of fields is the original baseline catalog. The second
    block (popularity … duration_sec) are the "advanced features" added in
    Challenge 1. They carry defaults so older code that builds a Song with only
    the baseline fields keeps working.
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
    # --- Advanced features (Challenge 1) ---
    popularity: int = 50                       # 0–100 chart-style popularity
    release_decade: int = 2010                 # e.g. 1990, 2000, 2010, 2020
    mood_tags: List[str] = field(default_factory=list)  # e.g. ["nostalgic","euphoric"]
    language: str = "english"                  # english, spanish, korean, instrumental…
    is_explicit: bool = False                  # explicit lyrics flag
    duration_sec: int = 210                    # track length in seconds

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py

    Baseline fields first, then optional preferences for the advanced features.
    The advanced ones default to None/True so existing profiles keep scoring
    exactly as before — a rule only fires when the user actually expresses it.
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    # --- Advanced preferences (Challenge 1) ---
    target_decade: Optional[int] = None
    preferred_mood_tags: Optional[List[str]] = None
    preferred_language: Optional[str] = None
    prefers_popular: Optional[bool] = None     # True = chart-chaser, False = crate-digger
    allow_explicit: bool = True

def _profile_to_prefs(user: UserProfile) -> Dict:
    """Bridge the UserProfile dataclass to the dict shape score_song expects."""
    prefs: Dict = {
        "genre": user.favorite_genre,
        "mood": user.favorite_mood,
        "energy": user.target_energy,
        "likes_acoustic": user.likes_acoustic,
        "allow_explicit": user.allow_explicit,
    }
    # Only include advanced keys the user actually set, so absent preferences
    # stay silent instead of matching an empty value.
    if user.target_decade is not None:
        prefs["decade"] = user.target_decade
    if user.preferred_mood_tags:
        prefs["mood_tags"] = user.preferred_mood_tags
    if user.preferred_language:
        prefs["language"] = user.preferred_language
    if user.prefers_popular is not None:
        prefs["prefers_popular"] = user.prefers_popular
    return prefs


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

    def recommend(
        self,
        user: UserProfile,
        k: int = 5,
        strategy: Optional["ScoringStrategy"] = None,
        diversity: bool = False,
    ) -> List[Song]:
        """Score every song for this user and return the top k, best first.

        Delegates to recommend_songs() so the class and CLI rank identically.
        Optionally accepts a scoring `strategy` (Challenge 2) and a `diversity`
        toggle (Challenge 3).
        """
        prefs = _profile_to_prefs(user)
        song_dicts = [asdict(s) for s in self.songs]
        results = recommend_songs(
            prefs, song_dicts, k=k, strategy=strategy, diversity=diversity
        )
        by_id = {s.id: s for s in self.songs}
        return [by_id[song["id"]] for song, _score, _expl in results]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return the plain-English reasons this song earned its score."""
        prefs = _profile_to_prefs(user)
        _score, reasons = score_song(prefs, asdict(song))
        return "; ".join(reasons) if reasons else "no strong matches"

def load_songs(csv_path: str) -> List[Dict]:
    """Read the CSV catalog into a list of song dicts, with fields typed.

    Numeric columns become int/float, the explicit flag becomes a real bool,
    and the pipe-separated mood_tags column becomes a list of strings.
    """
    int_fields = {"id", "tempo_bpm", "popularity", "release_decade", "duration_sec"}
    float_fields = {"energy", "valence", "danceability", "acousticness"}
    bool_fields = {"is_explicit"}
    list_fields = {"mood_tags"}  # stored as "tag1|tag2|tag3" in the CSV

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
                elif key in bool_fields:
                    song[key] = value.strip().lower() in ("true", "1", "yes")
                elif key in list_fields:
                    song[key] = [t.strip() for t in value.split("|") if t.strip()]
                else:
                    song[key] = value
            songs.append(song)

    return songs

# The normalized audio features (energy, valence, danceability, acousticness)
# all live on a 0.0–1.0 scale. Preferences are validated against this range so
# a malformed input can't push the score outside its designed bounds.
FEATURE_MIN, FEATURE_MAX = 0.0, 1.0

# The keys score_song can act on. Used to tell a real profile apart from an
# empty / all-unknown one (which otherwise ranks silently by danceability).
PREFERENCE_KEYS = (
    "genre", "mood", "energy", "likes_acoustic",
    "decade", "mood_tags", "language", "prefers_popular",
)

# Moods that, in this catalog, describe inherently low- or high-energy songs.
# Used only to *warn* about self-contradictory profiles — the user is still
# free to ask for them, they just get told the request fights itself.
LOW_ENERGY_MOODS = {"sad", "melancholic", "relaxed", "chill", "dreamy"}
HIGH_ENERGY_MOODS = {"intense", "energetic", "euphoric", "confident", "dark"}

# Genres that are almost never acoustic; pairing them with likes_acoustic=True
# is a contradiction worth surfacing.
RARELY_ACOUSTIC_GENRES = {"metal", "electronic", "edm", "synthwave", "techno"}

# The default point values for every scoring rule. Scoring modes (Challenge 2)
# are just different weightings of this same recipe, so all the rules live in
# one place and the strategies only re-weight them.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "genre": 3.0,
    "mood": 2.0,
    "energy": 2.0,
    "acoustic": 1.0,
    "danceability": 0.5,
    # advanced-feature rules (Challenge 1)
    "popularity": 1.5,
    "decade": 1.0,
    "mood_tags": 1.0,
    "language": 1.0,
    "explicit_penalty": 2.0,
}


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


def score_song(
    user_prefs: Dict, song: Dict, weights: Optional[Dict[str, float]] = None
) -> Tuple[float, List[str]]:
    """Score one song against the user's taste and return (score, reasons).

    Implements the "VibeMatch" recipe: every song starts at 0 points and earns
    points for each way it matches the user's taste. Each rule that fires also
    appends a plain-English reason, so every score arrives with its receipt.

    `weights` lets a scoring mode (Challenge 2) re-weight the rules without
    duplicating them. When omitted, the balanced DEFAULT_WEIGHTS are used, which
    reproduces the original scores exactly.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    score = 0.0
    reasons: List[str] = []

    # Rule 1 — Genre match. The strongest single signal of taste.
    if song.get("genre") == user_prefs.get("genre"):
        pts = weights["genre"]
        score += pts
        reasons.append(f"genre match: {song['genre']} (+{pts:.1f})")

    # Rule 2 — Mood match.
    if song.get("mood") == user_prefs.get("mood"):
        pts = weights["mood"]
        score += pts
        reasons.append(f"mood match: {song['mood']} (+{pts:.1f})")

    # Rule 3 — Energy fit (graded): weight x (1 - |energy - target_energy|).
    # The target and closeness are both clamped to [0, 1] so a malformed input
    # (e.g. energy=2.0) can never make this term go NEGATIVE — it degrades to
    # "no energy bonus" instead.
    target_energy = user_prefs.get("energy")
    if target_energy is not None and song.get("energy") is not None:
        safe_target = _clamp(target_energy)
        closeness = _clamp(1.0 - abs(song["energy"] - safe_target))
        energy_points = weights["energy"] * closeness
        score += energy_points
        reasons.append(
            f"energy fit: {song['energy']} vs target {safe_target} "
            f"({energy_points:+.2f})"
        )

    # Rule 4 — Acoustic fit. Rewards acoustic songs for acoustic lovers, and
    # produced songs for everyone else. Only evaluated if the user stated it.
    if "likes_acoustic" in user_prefs:
        likes_acoustic = user_prefs["likes_acoustic"]
        acousticness = song.get("acousticness")
        if acousticness is not None:
            pts = weights["acoustic"]
            if likes_acoustic and acousticness >= 0.6:
                score += pts
                reasons.append(f"acoustic fit: acousticness {acousticness} (+{pts:.1f})")
            elif not likes_acoustic and acousticness <= 0.3:
                score += pts
                reasons.append(f"produced fit: acousticness {acousticness} (+{pts:.1f})")

    # Rule 5 — Danceability bonus. A gentle tie-breaker.
    if song.get("danceability", 0.0) >= 0.7:
        pts = weights["danceability"]
        score += pts
        reasons.append(f"danceable: {song['danceability']} (+{pts:.1f})")

    # ------------------------------------------------------------------ #
    # Advanced-feature rules (Challenge 1). Each fires only when the user   #
    # expresses the matching preference, so baseline profiles are untouched.#
    # ------------------------------------------------------------------ #

    # Rule 6 — Popularity. A chart-chaser (prefers_popular=True) is rewarded for
    # popular songs; a crate-digger (False) is rewarded for hidden gems.
    if "prefers_popular" in user_prefs and song.get("popularity") is not None:
        pop = song["popularity"]
        w = weights["popularity"]
        if user_prefs["prefers_popular"]:
            pts = w * (pop / 100.0)
            score += pts
            reasons.append(f"popular: {pop}/100 (+{pts:.2f})")
        else:
            pts = w * (1.0 - pop / 100.0)
            score += pts
            reasons.append(f"hidden gem: {pop}/100 (+{pts:.2f})")

    # Rule 7 — Release decade match.
    if "decade" in user_prefs and song.get("release_decade") is not None:
        if song["release_decade"] == user_prefs["decade"]:
            pts = weights["decade"]
            score += pts
            reasons.append(f"decade match: {song['release_decade']}s (+{pts:.1f})")

    # Rule 8 — Detailed mood-tag overlap. Each shared tag adds points, capped at
    # two so one song can't run away with the score.
    if user_prefs.get("mood_tags") and song.get("mood_tags"):
        wanted = set(user_prefs["mood_tags"])
        overlap = [t for t in song["mood_tags"] if t in wanted]
        if overlap:
            n = min(len(overlap), 2)
            pts = weights["mood_tags"] * n
            score += pts
            reasons.append(f"mood tags: {', '.join(overlap)} (+{pts:.2f})")

    # Rule 9 — Language match.
    if "language" in user_prefs and song.get("language"):
        if song["language"] == user_prefs["language"]:
            pts = weights["language"]
            score += pts
            reasons.append(f"language match: {song['language']} (+{pts:.1f})")

    # Rule 10 — Explicit penalty. Subtracts points when a user who asked to
    # avoid explicit content is shown an explicit track.
    if user_prefs.get("allow_explicit") is False and song.get("is_explicit"):
        pts = weights["explicit_penalty"]
        score -= pts
        reasons.append(f"explicit penalty: '{song.get('title')}' is explicit (-{pts:.1f})")

    return score, reasons


@dataclass
class ScoringStrategy:
    """One interchangeable ranking strategy (a "Strategy" pattern, Challenge 2).

    A strategy is just a named re-weighting of the shared scoring rules, so the
    logic lives in one place (score_song) and modes stay tiny and modular.
    """
    name: str
    description: str
    weights: Dict[str, float]

    def score(self, user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
        return score_song(user_prefs, song, self.weights)


def _mode(**overrides: float) -> Dict[str, float]:
    """Build a weight set from the defaults with a few values overridden."""
    weights = dict(DEFAULT_WEIGHTS)
    weights.update(overrides)
    return weights


# The registry of available scoring modes. main.py lets the user switch between
# these; adding a new mode is a one-line entry here, no other code changes.
STRATEGIES: Dict[str, ScoringStrategy] = {
    "balanced": ScoringStrategy(
        "Balanced",
        "The default recipe — every rule at its normal weight.",
        DEFAULT_WEIGHTS,
    ),
    "genre-first": ScoringStrategy(
        "Genre-First",
        "Genre dominates; mood and energy barely matter.",
        _mode(genre=6.0, mood=1.0, energy=1.0),
    ),
    "mood-first": ScoringStrategy(
        "Mood-First",
        "Mood and mood-tags lead; genre takes a back seat.",
        _mode(mood=5.0, mood_tags=2.5, genre=1.5),
    ),
    "energy-focused": ScoringStrategy(
        "Energy-Focused",
        "Energy fit and danceability drive the ranking.",
        _mode(energy=6.0, danceability=1.5, genre=1.0, mood=1.0),
    ),
    "fresh-and-popular": ScoringStrategy(
        "Fresh & Popular",
        "Leans on chart popularity and release decade.",
        _mode(popularity=4.0, decade=3.0, genre=1.5),
    ),
}


def get_strategy(name: str) -> ScoringStrategy:
    """Look up a scoring mode by key, with a helpful error if it's unknown."""
    try:
        return STRATEGIES[name]
    except KeyError:
        options = ", ".join(STRATEGIES)
        raise ValueError(f"Unknown scoring mode '{name}'. Choose one of: {options}")


def _apply_diversity(
    scored: List[Tuple[Dict, float, List[str]]],
    k: int,
    artist_penalty: float,
    genre_penalty: float,
) -> List[Tuple[Dict, float, List[str]]]:
    """Greedily pick k songs while penalizing repeated artists / genres.

    This is the Diversity Penalty (Challenge 3). We walk the already-sorted
    list and, at each step, dock a candidate's score for every song ALREADY
    chosen that shares its artist (bigger penalty) or genre (smaller penalty),
    then take the current best. The result avoids stacking the top five with the
    same artist or genre, and each penalized pick says so in its reasons.
    """
    pool = list(scored)
    selected: List[Tuple[Dict, float, List[str]]] = []
    artist_counts: Dict[str, int] = {}
    genre_counts: Dict[str, int] = {}

    while pool and len(selected) < k:
        best_i, best_adj, best_penalty = 0, None, 0.0
        for i, (song, base, _reasons) in enumerate(pool):
            a_seen = artist_counts.get(song.get("artist"), 0)
            g_seen = genre_counts.get(song.get("genre"), 0)
            penalty = a_seen * artist_penalty + g_seen * genre_penalty
            adjusted = base - penalty
            if best_adj is None or adjusted > best_adj:
                best_i, best_adj, best_penalty = i, adjusted, penalty

        song, _base, reasons = pool.pop(best_i)
        annotated = list(reasons)
        if best_penalty > 0:
            bits = []
            if artist_counts.get(song.get("artist"), 0):
                bits.append(f"artist '{song.get('artist')}' already listed")
            if genre_counts.get(song.get("genre"), 0):
                bits.append(f"genre '{song.get('genre')}' repeated")
            annotated.append(f"diversity penalty: {', '.join(bits)} (-{best_penalty:.2f})")

        selected.append((song, best_adj, annotated))
        artist_counts[song.get("artist")] = artist_counts.get(song.get("artist"), 0) + 1
        genre_counts[song.get("genre")] = genre_counts.get(song.get("genre"), 0) + 1

    return selected


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    strategy: Optional[ScoringStrategy] = None,
    weights: Optional[Dict[str, float]] = None,
    diversity: bool = False,
    artist_penalty: float = 1.5,
    genre_penalty: float = 0.75,
) -> List[Tuple[Dict, float, str]]:
    """Score every song and return the top k as (song, score, explanation).

    - `strategy` (or raw `weights`) selects the scoring mode (Challenge 2).
    - `diversity` toggles the artist/genre diversity penalty (Challenge 3).

    Defaults reproduce the original behaviour: balanced weights, no diversity
    penalty, tie-break on higher danceability then lower id.
    """
    if strategy is not None:
        weights = strategy.weights

    # Judge every song, pairing it with its score + reasons.
    scored = [(song, *score_song(user_prefs, song, weights)) for song in songs]

    # Sort highest score first; break ties on danceability, then id.
    scored.sort(
        key=lambda item: (-item[1], -item[0].get("danceability", 0.0), item[0].get("id", 0))
    )

    if diversity:
        selected = _apply_diversity(scored, k, artist_penalty, genre_penalty)
    else:
        selected = scored[:k]

    # Turn each song's reasons into a single explanation string.
    return [
        (song, score, "; ".join(reasons) if reasons else "no strong matches")
        for song, score, reasons in selected
    ]
