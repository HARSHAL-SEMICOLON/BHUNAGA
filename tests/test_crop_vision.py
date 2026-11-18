"""
Looking at a photograph.

The tests that matter here are the refusals. A vision model that confidently
names a disease from a blurry photo, and a screen that turns that into a spray
recommendation, is the most harmful thing this project could ship.
"""

from __future__ import annotations

import json

import pytest

import config
from farmer import crop_vision
from farmer.crop_vision import Candidate, Observation


# ───────────────────────────── reading the reply ───────────────────────────

GOOD = {
    "crop": "onion",
    "plant_part": "leaf",
    "visible": ["yellow tips", "sunken pale lesions along the blade"],
    "candidates": [
        {"name": "purple blotch", "confidence": 72, "tells": "purple centre as it matures"},
        {"name": "nitrogen deficiency", "confidence": 30, "tells": "older leaves first"},
    ],
    "photo_problem": "",
}


def test_a_clean_reply_is_read():
    obs = crop_vision._parse(json.dumps(GOOD))
    assert obs.ok
    assert obs.crop == "onion"
    assert obs.best.name == "purple blotch"
    assert len(obs.visible) == 2


def test_json_wrapped_in_prose_and_fences_is_still_read():
    """Models do this constantly no matter how firmly you ask them not to."""
    raw = f"Sure! Here is the result:\n```json\n{json.dumps(GOOD)}\n```\nHope that helps."
    assert crop_vision._parse(raw).crop == "onion"


def test_candidates_are_ordered_by_confidence():
    muddled = dict(GOOD, candidates=[
        {"name": "low", "confidence": 10},
        {"name": "high", "confidence": 90},
        {"name": "middle", "confidence": 50},
    ])
    names = [c.name for c in crop_vision._parse(json.dumps(muddled)).candidates]
    assert names == ["high", "middle", "low"]


@pytest.mark.parametrize("raw", [
    "", "   ", "I'm sorry, I can't help with that.",
    "{not json at all}", "[]", "null",
])
def test_an_unreadable_reply_is_an_error_not_a_crash(raw):
    obs = crop_vision._parse(raw)
    assert not obs.ok
    assert obs.error


def test_a_nonsense_confidence_does_not_blow_up():
    bad = dict(GOOD, candidates=[{"name": "x", "confidence": "very high"}])
    assert crop_vision._parse(json.dumps(bad)).candidates[0].confidence == 0


def test_confidence_is_clamped_to_a_real_percentage():
    bad = dict(GOOD, candidates=[{"name": "x", "confidence": 900}])
    assert crop_vision._parse(json.dumps(bad)).candidates[0].confidence == 100


def test_a_candidate_with_no_name_is_dropped():
    bad = dict(GOOD, candidates=[{"confidence": 90}, {"name": "real", "confidence": 60}])
    cands = crop_vision._parse(json.dumps(bad)).candidates
    assert [c.name for c in cands] == ["real"]


# ─────────────────────── the floor under naming a disease ──────────────────

def test_a_weak_guess_is_not_confident_enough_to_name():
    obs = Observation(candidates=[Candidate("early blight", 40)])
    assert obs.confident_enough is False


def test_a_strong_guess_is():
    obs = Observation(candidates=[Candidate("early blight", 80)])
    assert obs.confident_enough is True


def test_no_candidates_is_never_confident_enough():
    assert Observation().confident_enough is False


def test_the_floor_moves_with_the_setting(monkeypatch):
    obs = Observation(candidates=[Candidate("early blight", 60)])
    monkeypatch.setattr(config, "VISION_MIN_CONFIDENCE", 50)
    assert obs.confident_enough is True
    monkeypatch.setattr(config, "VISION_MIN_CONFIDENCE", 70)
    assert obs.confident_enough is False


# ───────────────────────── what gets searched for ──────────────────────────

def test_the_search_is_built_from_what_was_seen_not_only_the_guess():
    """
    Searching the candidate name alone finds documents that already agree with
    the model. The symptoms are what might turn up the cause it missed.
    """
    obs = Observation(crop="onion", visible=["yellow tips", "pale lesions"],
                      candidates=[Candidate("purple blotch", 72)])
    query = obs.search_query()
    assert "onion" in query
    assert "yellow tips" in query
    assert "purple blotch" in query


def test_a_search_query_survives_an_empty_observation():
    assert Observation().search_query() == ""


# ───────────────────────────── the call itself ─────────────────────────────

def test_no_photo_is_rejected_before_any_token_is_spent():
    assert crop_vision.look(b"").error


def test_an_oversized_photo_is_rejected_before_sending(monkeypatch):
    monkeypatch.setattr(config, "VISION_MAX_BYTES", 10)
    assert "too large" in crop_vision.look(b"x" * 50).error


def test_a_missing_key_is_explained_rather_than_raised(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    assert crop_vision.look(b"x" * 50).error


def test_a_rate_limit_comes_back_as_a_readable_message(monkeypatch):
    from farmer import answer_writer

    class _Err(Exception):
        status_code = 429

    def boom():
        raise AssertionError("should not be reached")

    class _Client:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    raise _Err("Rate limit reached on tokens per day (TPD)")

    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(answer_writer, "_groq_client", lambda: _Client())
    obs = crop_vision.look(b"\xff\xd8\xff" + b"x" * 100)
    assert not obs.ok
    assert "daily token budget" in obs.error


# ───────────────────────────── shrinking ───────────────────────────────────

def test_a_large_photo_is_made_smaller_before_sending():
    pytest.importorskip("PIL")
    from PIL import Image
    import io as _io

    buf = _io.BytesIO()
    Image.new("RGB", (3000, 2000), (80, 140, 60)).save(buf, format="JPEG", quality=95)
    original = buf.getvalue()

    smaller = crop_vision.shrink(original, max_side=1024)
    assert len(smaller) < len(original)
    assert max(Image.open(_io.BytesIO(smaller)).size) == 1024


def test_something_that_is_not_an_image_is_passed_through_untouched():
    junk = b"this is not a photograph"
    assert crop_vision.shrink(junk) == junk
