# AI Interactions Log

Documentation of the agentic workflow used to build the four stretch
challenges: advanced features, multiple scoring modes, a diversity penalty, and
a formatted results table.

---

## Agentic Workflow (SF8)

### Challenge 1 — Advanced Song Features

**What task did I give the agent?**

Add 5+ complex attributes to the dataset and make the scoring account for them.

**Example prompt used:**

> "Add at least five advanced attributes to `data/songs.csv` — popularity
> (0–100), release decade, detailed mood tags, language, and an explicit flag —
> filling in realistic values for all 20 songs. Then update `load_songs` to
> parse them (mood tags are pipe-separated; explicit is a real boolean) and add
> new scoring rules in `score_song` so a user can express preferences for
> decade, mood tags, language, and popularity. Keep the baseline scores
> unchanged when the user doesn't set the new preferences."

**What the agent generated / changed:**

- `data/songs.csv`: 6 new columns — `popularity`, `release_decade`, `mood_tags`
  (pipe-separated), `language`, `is_explicit`, `duration_sec` — for all 20 rows.
- `src/recommender.py`:
  - `Song` and `UserProfile` dataclasses gained the new fields **with defaults**
    so old constructors still work.
  - `load_songs` now types ints/floats/bools and splits `mood_tags` into a list.
  - `score_song` gained Rules 6–10: popularity (chart-chaser vs crate-digger),
    decade match, mood-tag overlap, language match, and an explicit penalty.

**What I verified or fixed manually:**

- Ran the app and confirmed the new reasons appear (e.g. `mood tags: euphoric,
  party (+2.00)`, `decade match: 2020s (+1.0)`, `popular: 89/100 (+1.33)`).
- Checked that a **baseline profile with none of the new keys scores exactly the
  same as before** — the new rules are all gated on the user expressing the
  preference, so `pytest` still passes unchanged.
- Confirmed `is_explicit` is only `true` for HUMBLE. (realistic) and that the
  explicit penalty only fires when a profile sets `allow_explicit=False`.

---

## Design Pattern (SF10)

### Challenge 2 — Multiple Scoring Modes

**Which design pattern did I use?**

The **Strategy pattern**. Each ranking mode is an interchangeable strategy that
plugs into the same recommender.

**How AI helped me brainstorm / implement it:**

I attached `recommender.py` and asked the assistant to suggest a modular way to
support several ranking strategies without copy-pasting the scoring rules.

**Example prompt used:**

> "I want several ranking modes — Genre-First, Mood-First, Energy-Focused, and a
> popularity-based one — that a user can switch between in `main.py`. Suggest a
> simple Strategy pattern that keeps the code modular. I do NOT want to duplicate
> the scoring rules in each mode."

**The key insight from the brainstorm:** instead of writing a separate scoring
function per mode (which would duplicate all ten rules), make every mode a
**named set of weights** for the *one* shared `score_song`. The rules live in one
place; a strategy only changes how much each rule counts.

**How the pattern appears in the final code:**

- `ScoringStrategy` (a dataclass in `recommender.py`) holds a `name`,
  `description`, and a `weights` dict, and exposes a `score()` method that calls
  the shared `score_song(user_prefs, song, weights)`.
- `STRATEGIES` is a registry of ready-made modes (`balanced`, `genre-first`,
  `mood-first`, `energy-focused`, `fresh-and-popular`). Adding a mode is a
  one-line entry — no other code changes.
- `recommend_songs(..., strategy=...)` and `main.py` let you switch modes.

**What I verified manually:**

Ran one profile (funk + euphoric) through every mode. **Genre-First** promotes
the funk track (*Superstition*) to #1, while every other mode keeps the euphoric
all-rounder (*One More Time*) — proof the weights actually change the ranking,
not just the printed numbers.

### Challenge 3 — Diversity and Fairness Logic

**The rule I asked for (example prompt):**

> "Add a Diversity Penalty to the ranking. After scoring, when building the top
> results, penalize a song's score if its **artist is already present** in the
> chosen list (and a smaller penalty if its **genre** is already present). Pick
> greedily so the final top-5 doesn't stack the same artist or genre, and record
> the penalty in each song's reasons so it stays explainable."

**What the agent generated:**

`_apply_diversity()` in `recommender.py` — a greedy re-ranker. It walks the
already-sorted list and, at each pick, subtracts `artist_penalty` (1.5) for each
already-chosen song by the same artist and `genre_penalty` (0.75) per repeated
genre, then takes the current best. Penalized picks append a reason like
`diversity penalty: artist 'LoRoom' already listed, genre 'lofi' repeated
(-3.00)`. It's opt-in via `recommend_songs(..., diversity=True)`.

**What I verified manually:**

On a lofi profile, diversity OFF returned three lofi songs in the top three with
*LoRoom* appearing twice. With diversity ON, *LoRoom*'s second track drops from
rank 3 to rank 5 and two different genres move up — the top 5 is visibly more
varied.

### Challenge 4 — Visual Summary Table

**Example prompt used:**

> "Suggest a way to display the top recommendations as a formatted table using
> `tabulate` (with a plain-ASCII fallback if it isn't installed). The table
> **must include the reasons** for each song's score, not just the score."

**What the agent generated:**

`format_table()` in `main.py` builds a `tabulate` grid with columns `#`, Title,
Artist, Genre, Score, and **"Why it was picked"** (the reasons as a bulleted,
multi-line cell). If `tabulate` isn't importable, `_ascii_table()` prints the
same data with the reasons indented under each row. Added `tabulate` to
`requirements.txt`.

**What I verified manually:**

Ran `python -m src.main`; the header confirms `Table renderer: tabulate`, and
every row shows its full list of reasons inside the grid. Temporarily simulated a
missing `tabulate` to confirm the ASCII fallback path also renders the reasons.

---

## Overall manual verification

- `pytest` → **2 passed** after all four challenges (the OOP `Recommender`
  path still delegates to the shared functions).
- `python -m src.main` runs all four demos end-to-end with no errors.
- Confirmed backward compatibility: profiles that don't use the new features
  produce the same scores as before the changes.
