```mermaid
flowchart TD
    A["INPUT · User Prefs<br/>genre · mood · target_energy · likes_acoustic"] --> B["load_songs('data/songs.csv')<br/>→ list of song dicts"]
    B --> C{"More songs<br/>to judge?"}
    C -- "Yes: next song" --> D["score_song(user_prefs, song)<br/>→ (score, reasons)"]
    D --> L["append (song, score, explanation)<br/>to results"]
    L --> C
    C -- "No: all judged" --> M["sort by score, highest first<br/>tie-break: danceability, then id"]
    M --> N["OUTPUT · Top-K Recommendations<br/>(song, score, explanation)"]
```s