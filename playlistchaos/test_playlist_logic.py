"""Tests for playlist_logic.

Focused on the behavior that was previously buggy: classification, merging,
stats, search, and the lucky-pick helper. Run with:

    pytest test_playlist_logic.py
"""

from playlist_logic import (
    DEFAULT_PROFILE,
    build_playlists,
    classify_song,
    compute_playlist_stats,
    history_summary,
    lucky_pick,
    merge_playlists,
    most_common_artist,
    normalize_song,
    random_choice_or_none,
    search_songs,
)


def make_song(title, artist, genre, energy, tags=None):
    return {
        "title": title,
        "artist": artist,
        "genre": genre,
        "energy": energy,
        "tags": tags or [],
    }


# --- normalize_song ---------------------------------------------------------


def test_normalize_song_lowercases_and_strips():
    raw = {"title": "  Strobe ", "artist": " Deadmau5 ", "genre": " Electronic "}
    song = normalize_song(raw)
    assert song["title"] == "Strobe"
    assert song["artist"] == "deadmau5"
    assert song["genre"] == "electronic"


def test_normalize_song_coerces_string_energy_and_tag():
    song = normalize_song({"energy": "7", "tags": "synth"})
    assert song["energy"] == 7
    assert song["tags"] == ["synth"]


def test_normalize_song_handles_bad_energy():
    song = normalize_song({"energy": "loud"})
    assert song["energy"] == 0


# --- classify_song ----------------------------------------------------------


def test_classify_high_energy_is_hype():
    profile = dict(DEFAULT_PROFILE)
    profile["favorite_genre"] = "none"  # avoid favorite-genre shortcut
    song = normalize_song(make_song("Sandstorm", "Darude", "electronic", 10))
    assert classify_song(song, profile) == "Hype"


def test_classify_low_energy_is_chill():
    profile = dict(DEFAULT_PROFILE)
    profile["favorite_genre"] = "none"
    song = normalize_song(make_song("Weightless", "Marconi Union", "ambient", 1))
    assert classify_song(song, profile) == "Chill"


def test_classify_chill_keyword_matches_genre_not_title():
    # Regression: chill keywords ("lofi") must be detected via the genre.
    # A mid-energy lofi track should land in Chill even with a plain title.
    profile = dict(DEFAULT_PROFILE)
    profile["favorite_genre"] = "none"
    song = normalize_song(make_song("Afternoon", "DJ Calm", "lofi", 5))
    assert classify_song(song, profile) == "Chill"


def test_classify_mid_energy_other_genre_is_mixed():
    profile = dict(DEFAULT_PROFILE)
    profile["favorite_genre"] = "none"
    song = normalize_song(make_song("Take Five", "Dave Brubeck", "jazz", 5))
    assert classify_song(song, profile) == "Mixed"


# --- merge_playlists --------------------------------------------------------


def test_merge_does_not_mutate_inputs():
    # Regression: merge previously aliased and extended the caller's list.
    a = {"Hype": [make_song("A", "x", "rock", 9)]}
    b = {"Hype": [make_song("B", "y", "pop", 8)]}
    merged = merge_playlists(a, b)

    assert len(merged["Hype"]) == 2
    # The originals must be untouched.
    assert len(a["Hype"]) == 1
    assert len(b["Hype"]) == 1


def test_merge_handles_disjoint_keys():
    a = {"Hype": [make_song("A", "x", "rock", 9)]}
    b = {"Chill": [make_song("C", "z", "ambient", 1)]}
    merged = merge_playlists(a, b)
    assert set(merged.keys()) == {"Hype", "Chill"}
    assert len(merged["Hype"]) == 1
    assert len(merged["Chill"]) == 1


# --- compute_playlist_stats -------------------------------------------------


def test_stats_counts_and_ratio():
    playlists = {
        "Hype": [make_song("A", "x", "rock", 8), make_song("B", "x", "rock", 9)],
        "Chill": [make_song("C", "y", "ambient", 1)],
        "Mixed": [make_song("D", "z", "jazz", 5)],
    }
    stats = compute_playlist_stats(playlists)

    assert stats["total_songs"] == 4
    assert stats["hype_count"] == 2
    assert stats["chill_count"] == 1
    assert stats["mixed_count"] == 1
    # Regression: ratio is hype / all, not hype / hype (which was always 1.0).
    assert stats["hype_ratio"] == 0.5


def test_stats_average_energy_over_all_songs():
    playlists = {
        "Hype": [make_song("A", "x", "rock", 8)],
        "Chill": [make_song("C", "y", "ambient", 2)],
        "Mixed": [],
    }
    stats = compute_playlist_stats(playlists)
    # Regression: average over all songs => (8 + 2) / 2 == 5.0, not 8/2.
    assert stats["avg_energy"] == 5.0


def test_stats_empty_is_safe():
    stats = compute_playlist_stats({"Hype": [], "Chill": [], "Mixed": []})
    assert stats["total_songs"] == 0
    assert stats["hype_ratio"] == 0.0
    assert stats["avg_energy"] == 0.0
    assert stats["top_artist"] == ""


def test_most_common_artist():
    songs = [
        make_song("A", "Queen", "rock", 8),
        make_song("B", "Queen", "rock", 7),
        make_song("C", "Eagles", "rock", 6),
    ]
    artist, count = most_common_artist(songs)
    assert artist == "Queen"
    assert count == 2


# --- search_songs -----------------------------------------------------------


def test_search_matches_substring_of_field():
    # Regression: searching "dead" should match artist "deadmau5".
    songs = [
        normalize_song(make_song("Strobe", "Deadmau5", "electronic", 7)),
        normalize_song(make_song("Take Five", "Dave Brubeck", "jazz", 4)),
    ]
    results = search_songs(songs, "dead", field="artist")
    assert len(results) == 1
    assert results[0]["title"] == "Strobe"


def test_search_empty_query_returns_all():
    songs = [make_song("A", "x", "rock", 8)]
    assert search_songs(songs, "") == songs


def test_search_no_match_returns_empty():
    songs = [normalize_song(make_song("Strobe", "Deadmau5", "electronic", 7))]
    assert search_songs(songs, "queen", field="artist") == []


# --- lucky_pick / random_choice_or_none -------------------------------------


def test_random_choice_or_none_empty_returns_none():
    # Regression: must not raise IndexError on an empty list.
    assert random_choice_or_none([]) is None


def test_random_choice_or_none_returns_member():
    songs = [make_song("A", "x", "rock", 8)]
    assert random_choice_or_none(songs) in songs


def test_lucky_pick_empty_playlists_returns_none():
    playlists = {"Hype": [], "Chill": [], "Mixed": []}
    assert lucky_pick(playlists, mode="any") is None


def test_lucky_pick_hype_mode_only_picks_hype():
    hype = make_song("A", "x", "rock", 9)
    playlists = {"Hype": [hype], "Chill": [make_song("C", "y", "ambient", 1)]}
    assert lucky_pick(playlists, mode="hype") == hype


# --- build_playlists / history_summary --------------------------------------


def test_build_playlists_assigns_mood_label():
    profile = dict(DEFAULT_PROFILE)
    songs = [make_song("Sandstorm", "Darude", "electronic", 10)]
    playlists = build_playlists(songs, profile)
    assert playlists["Hype"][0]["mood"] == "Hype"


def test_history_summary_counts_moods():
    history = [
        {"mood": "Hype"},
        {"mood": "Hype"},
        {"mood": "Chill"},
        {"mood": "Unknown"},  # falls through to Mixed bucket
    ]
    summary = history_summary(history)
    assert summary["Hype"] == 2
    assert summary["Chill"] == 1
    assert summary["Mixed"] == 1
