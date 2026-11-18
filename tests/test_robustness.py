"""
The two things that protect the free tier.

This project runs on a budget of 200,000 tokens a day. With the council on,
one question is four model calls. So the two failure modes that actually bite
are: spending tokens on a question already answered, and retrying forever
against a quota that will not come back for hours.
"""

from __future__ import annotations

import pytest

import config
from farmer import answer_writer
from farmer.searcher import RetrievedChunk

CHUNKS = [RetrievedChunk("some guidance about urea", "wheat.md", "en", 0.9)]


# ═══════════════════ telling one 429 from another ═══════════════════

class _Err(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status_code = status


@pytest.mark.parametrize("message", [
    "Rate limit reached for model `openai/gpt-oss-120b` on tokens per day (TPD)",
    "429 you have exceeded your requests per day (RPD)",
])
def test_a_daily_quota_is_recognised_as_hopeless(message):
    kind, said = answer_writer.classify_failure(_Err(message, 429))
    assert kind == "daily"
    # it has to say what to do, not just what went wrong
    assert "council" in said.lower()


def test_a_burst_limit_is_recognised_as_worth_waiting_for():
    kind, _ = answer_writer.classify_failure(
        _Err("Rate limit reached: too many requests per minute", 429))
    assert kind == "burst"


@pytest.mark.parametrize("status", [500, 502, 503])
def test_server_errors_are_transient(status):
    assert answer_writer.classify_failure(_Err("upstream", status))[0] == "transient"


@pytest.mark.parametrize("message,status", [
    ("Invalid API Key provided", 401),
    ("unauthorized", 403),
])
def test_a_bad_key_is_never_retried(message, status):
    kind, said = answer_writer.classify_failure(_Err(message, status))
    assert kind == "auth"
    assert "GROQ_API_KEY" in said


def test_a_dropped_connection_is_transient():
    assert answer_writer.classify_failure(
        Exception("Connection aborted, timed out"))[0] == "transient"


# ═══════════════════ the retry policy ═══════════════════

def _always_fail(monkeypatch, exc, sleeps):
    calls = {"n": 0}

    class _Completions:
        def create(self, **kw):
            calls["n"] += 1
            raise exc

    class _Client:
        chat = type("c", (), {"completions": _Completions()})()

    monkeypatch.setattr(answer_writer, "_groq_client", lambda: _Client())
    monkeypatch.setattr(answer_writer.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(config, "GROQ_REASONING_EFFORT", "")
    return calls


def test_a_daily_quota_is_not_retried_even_once(monkeypatch):
    """Retrying a spent daily budget is two minutes of waiting for nothing."""
    sleeps = []
    calls = _always_fail(monkeypatch, _Err("rate limit on tokens per day", 429), sleeps)
    with pytest.raises(RuntimeError, match="daily token budget"):
        answer_writer.chat("sys", "user")
    assert calls["n"] == 1
    assert sleeps == []


def test_a_transient_failure_is_retried_a_bounded_number_of_times(monkeypatch):
    sleeps = []
    calls = _always_fail(monkeypatch, _Err("service unavailable", 503), sleeps)
    with pytest.raises(RuntimeError):
        answer_writer.chat("sys", "user")
    assert calls["n"] == answer_writer.MAX_RETRIES + 1
    assert len(sleeps) == answer_writer.MAX_RETRIES


def test_a_bad_key_is_reported_immediately(monkeypatch):
    sleeps = []
    calls = _always_fail(monkeypatch, _Err("Invalid API Key", 401), sleeps)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        answer_writer.chat("sys", "user")
    assert calls["n"] == 1


# ═══════════════════ the answer cache ═══════════════════

@pytest.fixture
def one_call(monkeypatch):
    """Count how many times the model is actually reached."""
    calls = {"n": 0}

    def fake(query, chunks, lang):
        calls["n"] += 1
        return "an answer"

    monkeypatch.setattr(answer_writer, "_generate_with_groq", fake)
    return calls


def test_the_same_question_is_answered_once_and_then_remembered(one_call):
    first = answer_writer.generate("how much urea", "en", CHUNKS, use_council=False)
    second = answer_writer.generate("how much urea", "en", CHUNKS, use_council=False)
    assert one_call["n"] == 1
    assert second.text == first.text
    assert first.cached is False and second.cached is True


def test_a_different_question_is_not_served_from_the_cache(one_call):
    answer_writer.generate("how much urea", "en", CHUNKS, use_council=False)
    answer_writer.generate("when to sow soybean", "en", CHUNKS, use_council=False)
    assert one_call["n"] == 2


def test_the_same_question_in_another_language_is_a_different_question(one_call):
    answer_writer.generate("how much urea", "en", CHUNKS, use_council=False)
    answer_writer.generate("how much urea", "mr", CHUNKS, use_council=False)
    assert one_call["n"] == 2


def test_new_documents_invalidate_the_answer(one_call):
    """
    The key includes the retrieved text, not just the question.

    Re-ingesting the corpus changes what the answer should be. A cache that
    ignored that would keep quoting a document that has since been replaced.
    """
    answer_writer.generate("how much urea", "en", CHUNKS, use_council=False)
    revised = [RetrievedChunk("revised guidance about urea", "wheat.md", "en", 0.9)]
    answer_writer.generate("how much urea", "en", revised, use_council=False)
    assert one_call["n"] == 2


def test_the_cache_does_not_grow_without_limit(one_call, monkeypatch):
    monkeypatch.setattr(config, "GEN_CACHE_SIZE", 3)
    for i in range(10):
        answer_writer.generate(f"question {i}", "en", CHUNKS, use_council=False)
    assert len(answer_writer._ANSWERS) == 3


def test_the_cache_can_be_switched_off(one_call, monkeypatch):
    monkeypatch.setattr(config, "GEN_CACHE_SIZE", 0)
    answer_writer.generate("how much urea", "en", CHUNKS, use_council=False)
    answer_writer.generate("how much urea", "en", CHUNKS, use_council=False)
    assert one_call["n"] == 2
