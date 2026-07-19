# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeMatch 1.0** — it matches your "vibe" to songs.

---

## 2. Goal / Task

VibeMatch suggests songs you might like. You tell it your taste. It gives you a
short, ranked list back.

- You give it four things: a favorite genre, a favorite mood, a target energy
  level (0 to 1), and whether you like acoustic music.
- It looks at every song in the catalog and gives each one a score.
- It returns the top 5 songs, best first, with a plain-English reason for each.

It does not "predict the future" or learn from other people. It just measures
how well each song fits the taste you typed in.

---

## 3. Algorithm Summary

Think of it like a judge handing out points. Every song starts at 0 points. It
earns points for each way it matches your taste. The song with the most points
wins.

Here is how a song earns points:

- **Same genre as you:** +3 points. This is the biggest reward.
- **Same mood as you:** +2 points.
- **Close to your energy level:** up to +2 points. A perfect energy match gets
  the full 2; the further off it is, the less it gets.
- **Acoustic fit:** +1 point. Acoustic songs if you like acoustic, produced
  songs if you don't.
- **Easy to dance to:** +0.5 points. A small tie-breaker.

Then it sorts every song from most points to fewest and shows you the top 5.

**Changes I made from the starter:** I built the scoring and ranking from the
starter stubs. I also added three safety checks: energy values outside 0–1 get
capped instead of breaking the math, an empty profile gets a clear warning, and
a self-contradictory profile (like "sad but high-energy") gets flagged so you
know the list is a compromise.

---

## 4. Data Used

- **Size:** a tiny catalog of **20 songs** in one CSV file (`data/songs.csv`).
- **Features per song:** genre, mood, energy, tempo, valence (how happy it
  sounds), danceability, and acousticness. My scoring only uses genre, mood,
  energy, danceability, and acousticness — it ignores tempo and valence.
- **Variety:** 17 different genres and 16 different moods. Most genres appear
  only once. The most common are lofi (3 songs) and pop (2 songs).
- **Changes:** I did not add or remove any songs. I used the catalog as given.
- **What's missing:** the catalog is far too small to represent real musical
  taste. Whole worlds of music (and language, lyrics, and culture) are missing,
  and with 17 genres in 20 songs, most genres have just one example.

---

## 5. Strengths

- **Clear, honest matches.** For a normal, consistent user (like "high-energy
  happy pop"), the top picks make sense and match intuition.
- **It always shows its work.** Every recommendation lists the exact reasons it
  earned its score, so you can see *why* a song was picked.
- **Easy to tune.** The point values are simple numbers, so changing what the
  system cares about is a one-line edit.
- **It doesn't crash on weird input.** Empty profiles, out-of-range numbers, and
  contradictory tastes all produce a sensible result plus a warning.

---

## 6. Limitations and Bias

**Weakness discovered: a high-energy "filter bubble" created by the energy gap
and the danceability bonus.** My scoring awards a song up to **+2.0** for how
close its energy is to the user's target, plus a flat **+0.5** if it is
danceable — and a song collects *both* of these even when its genre and mood
match the user not at all. As a result, a small cluster of loud, danceable,
heavily-produced tracks (Gym Hero, Dynamite, One More Time, Sunrise City) floats
into the top five of almost every energetic profile: across my six test users,
**Gym Hero alone appeared in five of them.** The flip side is that quiet,
acoustic songs naturally have low danceability, so they *never* earn that +0.5
and are quietly pushed down — meaning listeners who want calm, mellow music get
a flatter, less differentiated ranking than upbeat listeners do. The
empty-profile test makes the bias explicit: with no preferences stated at all,
the system falls back to ranking by danceability, effectively assuming that the
"default" listener wants dance music. So the energy gap never *refuses* a user,
but it steadily narrows everyone toward the same energetic, danceable middle and
under-serves the low-energy and niche-genre corners of taste.

**Other known limitations** (see the README stress test for detail): rigid
categorical matching means near-neighbors like "metal" and "rock" score as total
strangers; the score ignores `tempo_bpm` and `valence` entirely; and with 17
genres spread over just 20 songs, most genres have a single representative that
can only ever win for a user who names it exactly.

---

## 7. Evaluation

I evaluated the recommender by running it against **six user profiles** at once
(`python -m src.main`) and reading the top-5 list each one produced. Three were
ordinary tastes and three were deliberately "adversarial" — built to see whether
the scoring could be tricked:

| # | Profile | Preferences | Purpose |
| --- | --- | --- | --- |
| A | High-Energy Pop | pop · happy · energy 0.9 · produced | Everything points one way |
| B | Chill Lofi | lofi · chill · energy 0.30 · acoustic | Low-energy study listener |
| C | Deep Intense Rock | rock · intense · energy 0.95 · produced | Loud, produced |
| D | Conflicting | metal · **sad** · energy **0.9** · **acoustic** | Every signal fights another |
| E | Empty | `{}` | No preferences at all |
| F | Out-of-Range Energy | pop · happy · energy **2.0** | Invalid input |

**What I looked for:** whether the top picks actually matched the stated taste,
whether the same songs kept reappearing across very different users, and whether
bad input broke the ranking.

**What surprised me:**

- **One song, five lists.** *Gym Hero* — an intense workout track — showed up in
  five of the six profiles (A, C, D, E, F). I expected each user to get a
  distinct list; instead a handful of loud, danceable songs dominated almost
  everyone. This is the filter bubble described in Section 6.
- **A sad ballad crashed a chill-study list.** In profile B, Adele's *Someone
  Like You* (a sad soul song, neither lofi nor chill) reached #5 purely on a
  perfect energy match plus the acoustic bonus — proving the numeric terms can
  outvote the genre/mood labels.
- **Metal and rock are strangers.** Profile C (rock fan) never sees *Enter
  Sandman*, and profile D (metal fan) never sees *Storm Runner*, even though the
  two genres are musically close. Exact-string matching treats them as unrelated.
- **A contradiction gets split, not flagged (originally).** Profile D's #1 and #2
  (*Enter Sandman* vs *Someone Like You*) are near-opposites — the system served
  each half of a self-contradictory request separately. (I later added conflict
  warnings so this is now announced; see the README.)

### In plain language: why does "Gym Hero" keep showing up for "Happy Pop" fans?

Imagine you tell the app, *"I want happy pop music,"* and it hands you **Gym
Hero — an intense gym workout track — as your #2 pick.** Here's why. The app
rates every song on four questions: *Is the genre right? Is the mood right? Is
the energy about right? Is it easy to dance to?* Gym Hero is **pop** (match!),
it's **high-energy** (close enough!), and it's **very danceable** (bonus points!).
It only misses on **mood** — it's "intense," not "happy." But mood is just one of
four checks, and losing that one point isn't enough to knock the song out when it
wins the other three. So the app quietly treats *"happy pop"* and *"intense pop"*
as almost the same thing, as long as both are upbeat and danceable. To a person,
a cheerful sing-along and a sweaty gym anthem feel completely different — but to
the app they look like cousins, because it can't really "hear" the difference
between happy and intense once the energy is high.

### Pairwise comparisons (all 15 pairs)

For each pair of profiles, one comment on what changed and why it makes sense:

| Pair | What changed between the two lists — and why it makes sense |
| --- | --- |
| **A ↔ B** | Complete opposites, zero shared songs: A is loud danceable pop (Sunrise City, Gym Hero), B is quiet acoustic lofi (Library Rain, Midnight Coding). The energy gap does exactly its job — a song that scores high for a 0.9-energy user scores low for a 0.30-energy user. |
| **A ↔ C** | Both want high energy + produced, so they **share 4 of 5 songs** (Gym Hero, Dynamite, One More Time, Sunrise City); only the #1 differs (pop *Sunrise City* vs rock *Storm Runner*). Shows genre only decides the very top — below that, the same high-energy pool fills both lists. |
| **A ↔ D** | Both high-energy, so both surface Gym Hero / Dynamite / One More Time in the tail — but A's top is coherent pop while D's top is split between metal and a sad ballad. A clean profile gets a coherent list; a contradictory one gets a fractured one. |
| **A ↔ E** | A has clear winners up to 8.34; E flattens everything to 0.50 and ranks by danceability alone. They still **share Gym Hero and One More Time** — because danceability is the *only* thing E rewards, and it's also a big reason those songs rank for A. Reveals the hidden danceability default. |
| **A ↔ F** | **Nearly identical** — same five songs, same order. F's absurd energy=2.0 is clamped to 1.0, barely above A's 0.9, so scores only dip slightly (Sunrise City 8.34 → 8.14). Shows the clamp fix turns nonsense input into a sane neighbor instead of breaking the ranking. |
| **B ↔ C** | Total opposites again, no overlap: B is calm/acoustic, C is loud/produced. The energy gap cleanly separates the two ends of the scale. |
| **B ↔ D** | They share exactly **one** song — *Someone Like You* — ranked #5 for B but #2 for D. The sad acoustic ballad is the single track that serves both a calm listener *and* the "sad + acoustic" half of the contradictory metal user. |
| **B ↔ E** | No overlap, and they pull in **opposite directions**: B rewards quiet acoustic songs (which have *low* danceability), while E rewards danceability *only*. Strong evidence that the danceability default actively ignores calm-music lovers. |
| **B ↔ F** | Opposites, no shared songs — F wants maximum energy, B wants minimum. Same clean split as A↔B. |
| **C ↔ D** | Both lean heavy/high-energy and share Gym Hero / Dynamite / One More Time, but C leads with rock *Storm Runner* and D with metal *Enter Sandman* — and **neither song ever appears in the other's list**. A direct picture of rigid genre matching: metal ≠ rock. |
| **C ↔ E** | Share Gym Hero and One More Time, but C earns them through mood+energy while E gives them 0.50 on danceability alone. Same songs, completely different reasons. |
| **C ↔ F** | Both high-energy; share Gym Hero, Dynamite, One More Time, Sunrise City, differing only at #1 (rock vs pop). Same "genre decides the top, energy fills the rest" pattern as A↔C. |
| **D ↔ E** | Share Gym Hero, Dynamite, One More Time — the loud danceable cluster. D scores them ~2.4 on energy, E scores them 0.50 on danceability. Even a broken profile still leans on the same popular pool. |
| **D ↔ F** | Both high-energy and share the danceable cluster, but F is coherent pop (genre+mood both match) while D is fractured (metal + sad ballad). A well-formed profile — even an extreme one — produces a cleaner list than a contradictory one. |
| **E ↔ F** | Both are "bad input," but they fail differently: E can't tell songs apart at all (everything ties at 0.50), while F still ranks cleanly with an 8.14 top because genre and mood carry it. Shows the system needs at least one categorical signal — energy and danceability alone (E) can't differentiate. |

**Simple tests run:** the six-profile sweep above (repeatable via
`python -m src.main`), plus `pytest` for the sorting and explanation logic
(`2 passed`).

---

## 8. Intended Use and Non-Intended Use

**What it's for:**

- Learning and classroom exploration. It's a small, readable example of how a
  recommender turns data into ranked suggestions.
- Playing with scoring rules to *see* how changing the weights changes the
  output.
- Demoing why explainable, transparent scoring is useful.

**What it should NOT be used for:**

- Real product recommendations. The catalog is only 20 songs, so it can't serve
  actual listeners.
- Any decision that matters. It knows nothing about lyrics, language, culture, or
  real popularity, and it treats near-identical genres ("metal" vs "rock") as
  strangers.
- Judging a person's taste. A low score means "this catalog doesn't fit," not
  "your taste is wrong."

---

## 9. Ideas for Improvement

1. **Give partial credit for similar genres and moods.** Right now "metal" and
   "rock" score as total strangers. Teaching the system that they're close would
   fix the biggest blind spot.
2. **Add variety to the top 5.** A handful of loud, danceable songs show up for
   almost everyone. I'd add a rule that avoids stacking near-identical songs so
   the list feels more diverse.
3. **Use more of the data.** The songs already carry tempo and valence, but the
   score ignores them. Adding those would let the system tell apart songs that
   currently look the same.

---

## 10. Personal Reflection

The biggest thing this project taught me is that it is amazing how much data you
need to collect to make these suggestion algorithms as accurate as possible.
Working with only 20 songs, I could immediately feel the ceiling: the same few
tracks kept winning, whole genres had a single example, and there simply wasn't
enough information for the system to tell subtle tastes apart. My biggest
learning moment was watching one gym song, *Gym Hero*, surface for almost every
user I tested. That single result made the whole idea click — a recommendation
is really just points and sorting, and a couple of strong signals like energy
and danceability can quietly crowd out everything else. It showed me that when
real apps all seem to suggest the same popular songs, it is probably not a bug
but a side effect of how their scoring is weighted, and that better accuracy
mostly comes from feeding the model far more and far richer data than I had here.

Using AI tools sped up the parts that would have slowed me down the most —
scaffolding the scoring functions, generating the diverse test profiles, and
turning messy terminal output into clean explanations. Where I had to slow down
and double-check was anywhere the numbers actually mattered: I verified the point
math by hand, caught an energy calculation that could go negative on bad input,
and confirmed the genre counts myself instead of trusting a summary. The AI was a
great accelerator, but I still had to be the one who decided whether the output
was correct. What surprised me most was how convincing a simple, rule-based
system can feel — even with just five plain "if" rules and no learning at all,
the ranked lists genuinely read like real recommendations, which made me
appreciate both how little it takes to *seem* smart and how easily that
appearance can hide a bias. If I extended this project, I would start by
collecting a much larger and more balanced catalog, then teach the system that
similar genres and moods are related instead of strangers, and finally add a
rule that keeps the top five varied so a handful of loud, danceable songs can't
dominate everyone's results.
