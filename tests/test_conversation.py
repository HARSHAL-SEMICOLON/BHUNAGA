"""
Conversation memory.

The interesting tests here are the negative ones. Carrying context into a
question that did not need it is the failure mode that quietly degrades every
standalone answer, and it is invisible unless something checks for it.
"""

from __future__ import annotations

import pytest

from farmer import conversation
from farmer.conversation import History, Turn


# ───────────────────────────── follow-up detection ─────────────────────────

def test_nothing_is_a_follow_up_before_anything_has_been_said():
    assert History().is_follow_up("डोस किती?") is False


@pytest.mark.parametrize("question", [
    "डोस किती?",                       # mr fragment
    "कितना डालें?",                     # hi fragment
    "how much?",                       # en fragment
])
def test_a_fragment_after_a_question_is_a_follow_up(question):
    h = History()
    h.add("माझ्या कपाशीवर पांढरी माशी आहे", "Use neem oil.", "mr")
    assert h.is_follow_up(question) is True


@pytest.mark.parametrize("question", [
    "what is the dose for it",
    "क्या उसका छिड़काव सुबह करें",
    "त्याची फवारणी कधी करावी",
])
def test_a_question_pointing_backwards_is_a_follow_up(question):
    h = History()
    h.add("cotton has whitefly", "Use neem oil.", "en")
    assert h.is_follow_up(question) is True


@pytest.mark.parametrize("question", [
    "How much urea per acre for wheat?",
    "सोयाबीनची पेरणी कधी करावी?",
    "कपास में कीट नियंत्रण कैसे करें?",
    "How should I store onions after harvest?",
])
def test_a_standalone_question_is_never_treated_as_a_follow_up(question):
    """The expensive mistake: dragging the last crop into a fresh question."""
    h = History()
    h.add("माझ्या कपाशीवर पांढरी माशी आहे", "Use neem oil.", "mr")
    assert h.is_follow_up(question) is False


# ───────────────────────────── query expansion ─────────────────────────────

def test_a_follow_up_is_searched_for_with_the_earlier_subject():
    h = History()
    h.add("माझ्या कपाशीवर पांढरी माशी आहे", "Use neem oil.", "mr")
    expanded = h.expand("डोस किती?")
    assert "डोस किती?" in expanded
    assert "कपाशीवर" in expanded


def test_the_current_question_comes_first_so_it_dominates():
    h = History()
    h.add("cotton has whitefly", "Use neem oil.", "en")
    assert h.expand("how much?").startswith("how much?")


def test_a_standalone_question_is_passed_through_unchanged():
    h = History()
    h.add("cotton has whitefly", "Use neem oil.", "en")
    question = "How much urea per acre for wheat?"
    assert h.expand(question) == question


# ───────────────────────────── context block ───────────────────────────────

def test_a_standalone_question_carries_no_context_and_so_costs_nothing():
    h = History()
    h.add("cotton has whitefly", "Use neem oil at 5ml/litre.", "en")
    assert h.context_block("How much urea per acre for wheat?") == ""


def test_a_follow_up_carries_the_earlier_exchange():
    h = History()
    h.add("cotton has whitefly", "Use neem oil at 5ml/litre.", "en")
    block = h.context_block("how much?")
    assert "cotton has whitefly" in block
    assert "neem oil" in block


def test_a_long_answer_is_excerpted_rather_than_quoted_whole():
    h = History()
    h.add("cotton has whitefly", "x" * 2000, "en")
    block = h.context_block("how much?")
    assert len(block) < 2000
    assert "…" in block


# ───────────────────────────── bounds ──────────────────────────────────────

def test_history_keeps_only_the_most_recent_turns():
    h = History()
    for i in range(10):
        h.add(f"question {i}", f"answer {i}")
    assert len(h.turns) == conversation.MAX_TURNS
    assert h.turns[-1].question == "question 9"
    assert h.turns[0].question == f"question {10 - conversation.MAX_TURNS}"


def test_blank_questions_are_not_recorded():
    h = History()
    h.add("", "answer")
    h.add("   ", "answer")
    assert h.turns == []


# ───────────────────────── the screen's own format ─────────────────────────

def test_it_reads_the_list_the_ask_screen_already_keeps():
    items = [{"q": "cotton has whitefly", "answer": "Use neem oil.", "lang": "en"}]
    h = conversation.from_ui_history(items)
    assert h.last.question == "cotton has whitefly"
    assert h.is_follow_up("how much?") is True


@pytest.mark.parametrize("junk", [None, [], [None], ["not a dict"], [{}]])
def test_malformed_history_does_not_raise(junk):
    """Session state is not a contract; it must not be able to crash a question."""
    assert isinstance(conversation.from_ui_history(junk), History)


# ═══════════════════ wired into the assistant ═══════════════════

from dataclasses import dataclass, field  # noqa: E402

from farmer import assistant, searcher  # noqa: E402


@dataclass
class _Written:
    text: str = "an answer"
    council: object = None


def _capture(monkeypatch):
    """Record what the assistant actually searched for and asked with."""
    seen = {}

    def fake_retrieve(query, query_lang, top_k=None):
        seen["searched"] = query
        return [searcher.RetrievedChunk("chunk text", "doc.md", "en", 0.9)]

    def fake_generate(asked, query_lang, chunks):
        seen["asked"] = asked
        return _Written()

    monkeypatch.setattr("farmer.searcher.retrieve", fake_retrieve)
    monkeypatch.setattr("farmer.answer_writer.generate", fake_generate)
    return seen


def test_without_history_the_assistant_behaves_exactly_as_before(monkeypatch):
    """The phone channels pass no history; each call starts cold."""
    seen = _capture(monkeypatch)
    assistant.ask("How much urea per acre for wheat?", lang="en")
    assert seen["searched"] == "How much urea per acre for wheat?"
    assert "Earlier in this conversation" not in seen["asked"]


def test_a_follow_up_reaches_retrieval_with_the_earlier_subject(monkeypatch):
    seen = _capture(monkeypatch)
    history = History()
    history.add("how do I control whitefly on cotton", "Use neem oil.", "en")
    assistant.ask("what is the dose for it", lang="en", history=history)
    assert "whitefly" in seen["searched"]
    assert "Earlier in this conversation" in seen["asked"]


def test_a_standalone_question_is_unaffected_by_history(monkeypatch):
    seen = _capture(monkeypatch)
    history = History()
    history.add("how do I control whitefly on cotton", "Use neem oil.", "en")
    assistant.ask("How much urea per acre for wheat?", lang="en", history=history)
    assert seen["searched"] == "How much urea per acre for wheat?"
    assert "whitefly" not in seen["asked"]


def test_broken_history_cannot_take_the_answer_down(monkeypatch):
    """Memory is a convenience. It must never be the reason a question fails."""
    seen = _capture(monkeypatch)

    class Exploding:
        def expand(self, q): raise RuntimeError("boom")
        def context_block(self, q): raise RuntimeError("boom")

    reply = assistant.ask("How much urea for wheat?", lang="en",
                          history=Exploding())
    assert reply.ok
    assert seen["searched"] == "How much urea for wheat?"
