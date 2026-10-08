"""
Tests for the local fallback store and the question bank.

The store tests use hand-made vectors rather than real BGE-M3 output, so the
right answer is known in advance and nothing has to be downloaded. Eight
dimensions is enough to prove the ranking maths; the real model uses 1024, but
the arithmetic is identical.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from qdrant_client import models

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from farmer import question_bank as bank, vector_database
from farmer.local_store import LocalStore

DIM = 8


def vec(*axes):
    """A unit vector pointing along the given axes."""
    v = np.zeros(DIM, dtype=np.float32)
    for a in axes:
        v[a] = 1.0
    return v.tolist()


@pytest.fixture
def store(tmp_path):
    s = LocalStore(tmp_path / "kb")
    s.create_collection(config.QDRANT_COLLECTION)
    s.upsert(config.QDRANT_COLLECTION, [
        vector_database.build_point("p0", vec(0, 1), {10: 2.0, 11: 1.0},
                                    {"text": "urea for wheat", "source": "wheat.md",
                                     "source_lang": "en"}),
        vector_database.build_point("p1", vec(2, 3), {20: 2.0, 21: 1.0},
                                    {"text": "onion storage", "source": "onion.md",
                                     "source_lang": "en"}),
        vector_database.build_point("p2", vec(4, 5), {30: 2.0},
                                    {"text": "pm-kisan money", "source": "pmk.md",
                                     "source_lang": "hi"}),
    ])
    return s


def search(store, dense, sparse, limit=3):
    prefetch = [
        models.Prefetch(query=dense, using=config.DENSE_VECTOR_NAME, limit=30),
        models.Prefetch(query=vector_database.to_sparse_vector(sparse),
                        using=config.SPARSE_VECTOR_NAME, limit=30),
    ]
    return store.query_points(config.QDRANT_COLLECTION, prefetch=prefetch,
                              limit=limit)


# ------------------------------ the store ------------------------------ #
def test_empty_store_reports_itself_as_empty(tmp_path):
    s = LocalStore(tmp_path / "kb")
    assert not vector_database.collection_exists(s)
    assert s.count(config.QDRANT_COLLECTION).count == 0


def test_searching_an_empty_store_returns_nothing_rather_than_crashing(tmp_path):
    s = LocalStore(tmp_path / "kb")
    assert search(s, vec(0), {1: 1.0}).points == []


def test_upsert_then_count(store):
    assert store.count(config.QDRANT_COLLECTION).count == 3
    assert store.dense.shape == (3, DIM)


def test_both_signals_agreeing_puts_the_right_chunk_first(store):
    hits = search(store, vec(2, 3), {20: 2.0, 21: 1.0})
    assert hits.points[0].payload["source"] == "onion.md"


def test_dense_only_query_still_ranks(store):
    hits = search(store, vec(0, 1), {})
    assert hits.points[0].payload["source"] == "wheat.md"


def test_sparse_only_query_still_ranks(store):
    hits = search(store, vec(7), {10: 5.0})
    assert hits.points[0].payload["source"] == "wheat.md"


def test_disagreeing_signals_are_fused_not_dropped(store):
    """RRF should surface both candidates, which is the point of hybrid search."""
    found = [p.payload["source"] for p in search(store, vec(0, 1), {30: 2.0}).points]
    assert "wheat.md" in found and "pmk.md" in found


def test_limit_is_respected(store):
    assert len(search(store, vec(0, 1), {10: 1.0}, limit=2).points) == 2


def test_payload_survives_the_round_trip(store):
    payload = search(store, vec(0, 1), {10: 1.0}).points[0].payload
    assert payload["text"] == "urea for wheat"
    assert payload["source_lang"] == "en"


# ------------------------------ on disk -------------------------------- #
def test_reopening_finds_the_same_chunks(store, tmp_path):
    again = LocalStore(tmp_path / "kb")
    assert again.count(config.QDRANT_COLLECTION).count == 3
    assert vector_database.collection_exists(again)


def test_sparse_keys_come_back_as_ints_not_strings(store, tmp_path):
    """JSON has no integer keys, so this is a real trap and not a hypothetical."""
    again = LocalStore(tmp_path / "kb")
    key = next(iter(again.meta[0]["sparse"]))
    assert isinstance(key, int)


def test_reopened_store_still_searches(store, tmp_path):
    again = LocalStore(tmp_path / "kb")
    assert search(again, vec(2, 3), {20: 1.0}).points[0].payload["source"] == "onion.md"


def test_delete_clears_the_files(store, tmp_path):
    store.delete_collection(config.QDRANT_COLLECTION)
    assert LocalStore(tmp_path / "kb").count(config.QDRANT_COLLECTION).count == 0


def test_a_half_written_file_starts_clean_instead_of_limping(tmp_path):
    folder = tmp_path / "kb"
    folder.mkdir()
    (folder / "dense.npy").write_bytes(b"not a numpy file")
    (folder / "meta.json").write_text("{{{ broken")
    assert LocalStore(folder).count(config.QDRANT_COLLECTION).count == 0


# --------------------- choosing a backend ------------------------------ #
def test_unreachable_qdrant_falls_back_to_local(monkeypatch):
    vector_database.reset()
    monkeypatch.setattr(config, "VECTOR_BACKEND", "auto")
    monkeypatch.setattr(vector_database, "_try_qdrant",
                        lambda: (_ for _ in ()).throw(RuntimeError("404 Not Found")))
    vector_database.get_client()
    assert vector_database.backend() == "local"
    vector_database.reset()


@pytest.mark.parametrize("error,expect", [
    ("Unexpected Response: 404", "1.9"),
    ("Connection timed out", "did not answer in time"),
    ("getaddrinfo failed", "does not resolve"),
    ("401 Unauthorized", "API key was refused"),
])
def test_each_failure_gets_a_line_a_student_can_act_on(monkeypatch, error, expect):
    vector_database.reset()
    monkeypatch.setattr(config, "VECTOR_BACKEND", "auto")
    monkeypatch.setattr(vector_database, "_try_qdrant",
                        lambda: (_ for _ in ()).throw(RuntimeError(error)))
    vector_database.get_client()
    assert expect in vector_database.why_local()
    vector_database.reset()


def test_backend_qdrant_still_fails_loudly(monkeypatch):
    """If you asked for Qdrant specifically, silence would be the wrong answer."""
    vector_database.reset()
    monkeypatch.setattr(config, "VECTOR_BACKEND", "qdrant")
    monkeypatch.setattr(vector_database, "_try_qdrant",
                        lambda: (_ for _ in ()).throw(RuntimeError("down")))
    with pytest.raises(RuntimeError):
        vector_database.get_client()
    vector_database.reset()


def test_collection_exists_never_calls_the_1_9_only_endpoint():
    """
    The bug this replaced: client.collection_exists() asks an endpoint added in
    Qdrant 1.9, and older servers answer 404, which the client raises.
    """
    class OldServer:
        def get_collections(self):
            return type("R", (), {"collections": [
                type("C", (), {"name": config.QDRANT_COLLECTION})()]})()

        def collection_exists(self, name):
            raise RuntimeError("404 page not found")

    assert vector_database.collection_exists(OldServer()) is True


# --------------------------- question bank ----------------------------- #
def test_every_question_exists_in_all_three_languages():
    for q in bank.all_questions():
        assert q.en and q.hi and q.mr, q.en
        assert q.icon


def test_topics_are_labelled_in_all_three_languages():
    for topic in bank.TOPICS:
        for lang in ("en", "hi", "mr"):
            assert topic.label(lang)


def test_unknown_language_falls_back_to_english():
    q = bank.all_questions()[0]
    assert q.text("fr") == q.en


def test_an_empty_box_still_offers_somewhere_to_start():
    """An empty dropdown teaches a farmer nothing about what the app can do."""
    assert len(bank.suggest("", "en")) == len(bank.TOPICS)


@pytest.mark.parametrize("typed,expect", [
    ("urea", "urea"), ("onion", "onion"), ("insurance", "insurance"),
])
def test_typing_english_finds_the_question(typed, expect):
    found = " ".join(q.all_text().lower() for q in bank.suggest(typed, "en"))
    assert expect in found


@pytest.mark.parametrize("typed", ["कांदा", "गव्हा", "युरिया"])
def test_typing_devanagari_finds_the_question(typed):
    """
    Matras are combining marks, not letters. Stripping them as punctuation
    reduces "कांदा" to loose consonants and it matches nothing.
    """
    assert bank.suggest(typed, "mr"), typed


@pytest.mark.parametrize("typed,expect", [
    ("kanda", "onion"), ("kenchua", "earthworm"), ("bhav", "sell"),
    ("vima", "insurance"), ("nafa", "profit"),
])
def test_romanised_words_find_the_question(typed, expect):
    """Farmers type Marathi in English letters, because that is the keyboard."""
    found = " ".join(q.all_text().lower() for q in bank.suggest(typed, "en"))
    assert expect in found, f"{typed} -> {found[:120]}"


def test_every_romanised_hint_actually_leads_somewhere():
    """A hint pointing at a word no question contains is dead weight."""
    dead = [word for word in bank.ROMAN_HINTS if not bank.suggest(word, "en")]
    assert not dead, f"hints that match nothing: {dead}"


def test_nonsense_returns_nothing():
    assert bank.suggest("zzzqqq", "en") == []


def test_suggestions_respect_the_limit():
    assert len(bank.suggest("crop", "en", limit=2)) <= 2
