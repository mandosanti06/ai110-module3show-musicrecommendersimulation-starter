from src.recommender import Song, UserProfile, Recommender

def make_small_recommender() -> Recommender:
    # Deliberately list the lofi song FIRST so a stub that returns songs
    # unsorted (self.songs[:k]) cannot pass the sorting test by luck.
    songs = [
        Song(
            id=1,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
        Song(
            id=2,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # The pop, happy, high-energy song matches this user best, so it MUST rank
    # first — even though it is listed second in the catalog. This only passes
    # if recommend() actually scores and sorts, not if it returns input order.
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"
    assert results[1].genre == "lofi"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""
