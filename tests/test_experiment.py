"""
Tests for the three-arm experiment: self-consistency, resuming, and statistics.

None of these call a model. The point of the harness is that an interrupted
run loses nothing and a small sample is reported honestly, and both of those
are things you want to know work *before* you spend a day's token allowance
finding out they do not.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
import evaluate
from farmer import answer_writer, self_consistency, stats


class Chunk:
    def __init__(self, text="Apply 50 kg urea per acre.", source="wheat.md"):
        self.text, self.source, self.source_lang, self.score = (
            text, source, "en", 0.9)


CHUNKS = [Chunk()]


# ----------------------------------------------------- self-consistency
def test_the_odd_sample_out_loses(monkeypatch):
    """
    Three samples agree, one invents a number. The medoid must be one of the
    three — that is the whole mechanism.
    """
    replies = iter([
        "Apply 50 kg urea per acre in two doses.",
        "Apply 50 kg urea per acre, split into two doses.",
        "Apply 50 kg urea per acre across two doses.",
        "Apply 950 kg potash per hectare weekly.",      # the outlier
    ])
    monkeypatch.setattr(answer_writer, "chat", lambda **kw: next(replies))

    result = self_consistency.answer("q", CHUNKS, "English")
    assert "50 kg urea" in result.answer
    assert "950" not in result.answer


def test_it_costs_the_same_number_of_calls_as_the_council(monkeypatch):
    """
    The control is only a control if it spends what the council spends. The
    council is three experts plus a chairman; this must be four calls too.
    """
    calls = []
    monkeypatch.setattr(answer_writer, "chat",
                        lambda **kw: calls.append(1) or "an answer about urea")
    self_consistency.answer("q", CHUNKS, "English")
    assert len(calls) == config.SELFCONS_SAMPLES == 4


def test_samples_are_drawn_hot_enough_to_differ(monkeypatch):
    """
    At the single-agent temperature every sample comes back the same and the
    medoid means nothing. It must use the council's member temperature so the
    two arms differ in structure, not in how adventurous the model may be.
    """
    seen = []
    monkeypatch.setattr(answer_writer, "chat",
                        lambda **kw: seen.append(kw.get("temperature")) or "x y z")
    self_consistency.answer("q", CHUNKS, "English")
    assert set(seen) == {config.COUNCIL_MEMBER_TEMPERATURE}
    assert config.SELFCONS_TEMPERATURE > config.GEN_TEMPERATURE


def test_identical_samples_score_full_agreement(monkeypatch):
    monkeypatch.setattr(answer_writer, "chat", lambda **kw: "apply fifty kilo urea")
    assert self_consistency.answer("q", CHUNKS, "English").score == 100


def test_a_failed_sample_does_not_sink_the_arm(monkeypatch):
    calls = {"n": 0}

    def flaky(**kw):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("rate limited")
        return "apply fifty kilo urea per acre"

    monkeypatch.setattr(answer_writer, "chat", flaky)
    result = self_consistency.answer("q", CHUNKS, "English")
    assert result.answer and len(result.spoke) == 3


def test_every_sample_failing_raises_so_the_caller_can_fall_back(monkeypatch):
    def boom(**kw):
        raise RuntimeError("rate limited")
    monkeypatch.setattr(answer_writer, "chat", boom)
    with pytest.raises(RuntimeError):
        self_consistency.answer("q", CHUNKS, "English")


def test_generate_routes_the_three_modes(monkeypatch):
    monkeypatch.setattr(config, "GEN_CACHE_SIZE", 0)
    monkeypatch.setattr(answer_writer, "chat", lambda **kw: "sampled answer")
    monkeypatch.setattr(answer_writer, "_generate_with_groq",
                        lambda q, c, lang: "plain answer")

    single = answer_writer.generate("q", "en", CHUNKS, mode="single")
    assert single.council is None and single.text == "plain answer"

    sampled = answer_writer.generate("q", "en", CHUNKS, mode="selfcons")
    assert sampled.council is not None
    assert sampled.strategy.endswith("+selfcons")


def test_the_arms_do_not_share_a_cached_answer(monkeypatch):
    """
    If the cache key ignored the mode, the three arms would serve each other's
    answers and the whole comparison would collapse into one number repeated.
    """
    monkeypatch.setattr(config, "GEN_CACHE_SIZE", 64)
    answer_writer.clear_cache()
    monkeypatch.setattr(answer_writer, "chat", lambda **kw: "sampled answer")
    monkeypatch.setattr(answer_writer, "_generate_with_groq",
                        lambda q, c, lang: "plain answer")

    a = answer_writer.generate("q", "en", CHUNKS, mode="single")
    b = answer_writer.generate("q", "en", CHUNKS, mode="selfcons")
    assert a.text != b.text, "the modes shared a cache entry"


# ------------------------------------------------------------ statistics
def _rows(mode, values, metric="grounded"):
    return [{"id": f"q{i}", "lang": "en", "mode": mode, metric: v}
            for i, v in enumerate(values)]


def test_a_clear_difference_is_detected():
    worse = _rows("single", [0.2] * 20)
    better = _rows("council", [0.9] * 20)
    result = stats.compare(worse, better, "grounded")
    assert result.delta == pytest.approx(0.7, abs=0.01)
    assert result.significant and result.low > 0
    assert result.wins_b == 20


def test_no_difference_is_reported_as_no_difference():
    """The honest outcome, and the one a small study most often has."""
    a = _rows("single", [0.5, 0.6, 0.4, 0.5, 0.6, 0.4] * 3)
    b = _rows("council", [0.6, 0.5, 0.5, 0.4, 0.5, 0.5] * 3)
    result = stats.compare(a, b, "grounded")
    assert not result.significant
    assert "no reliable difference" in result.verdict("single", "council")


def test_noise_at_tiny_n_is_not_called_a_result():
    """Two questions apart out of twelve must not read as a finding."""
    a = _rows("single", [0.5] * 10 + [0.0, 0.0])
    b = _rows("council", [0.5] * 10 + [1.0, 1.0])
    assert not stats.compare(a, b, "grounded").significant


def test_pairing_is_on_the_question_not_the_order():
    a = [{"id": "q1", "lang": "en", "grounded": 0.0},
         {"id": "q2", "lang": "en", "grounded": 1.0}]
    b = [{"id": "q2", "lang": "en", "grounded": 1.0},   # reversed
         {"id": "q1", "lang": "en", "grounded": 0.0}]
    assert stats.compare(a, b, "grounded").delta == 0.0


def test_unanswered_rows_are_dropped_not_counted_as_zero():
    a = [{"id": "q1", "lang": "en", "grounded": 1.0},
         {"id": "q2", "lang": "en", "grounded": ""}]
    b = [{"id": "q1", "lang": "en", "grounded": 1.0},
         {"id": "q2", "lang": "en", "grounded": 1.0}]
    assert stats.compare(a, b, "grounded").n == 1


def test_the_interval_is_reproducible():
    a, b = _rows("single", [0.3] * 15), _rows("council", [0.7] * 15)
    first = stats.compare(a, b, "grounded")
    second = stats.compare(a, b, "grounded")
    assert (first.low, first.high) == (second.low, second.high)


# -------------------------------------------------------------- resuming
def test_finished_rows_are_recognised(tmp_path):
    log = tmp_path / "results.jsonl"
    rows = [{"id": "q1", "lang": "en", "strategy": "-", "mode": "council"},
            {"id": "q1", "lang": "en", "strategy": "-", "mode": "single"}]
    log.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    done = evaluate.load_done(log)
    assert len(done) == 2
    assert ("q1", "en", "-", "council") in done


def test_a_half_written_last_line_is_survived(tmp_path):
    """A run killed mid-write must not make the whole log unreadable."""
    log = tmp_path / "results.jsonl"
    log.write_text(
        json.dumps({"id": "q1", "lang": "en", "strategy": "-", "mode": "single"})
        + '\n{"id": "q2", "lang": "e',          # cut off
        encoding="utf-8")
    assert len(evaluate.load_done(log)) == 1


def test_a_missing_log_is_simply_empty(tmp_path):
    assert evaluate.load_done(tmp_path / "nope.jsonl") == {}


def test_the_plan_covers_every_arm_of_every_question():
    items = [{"id": "a", "questions": {"en": "?", "mr": "?"}},
             {"id": "b", "questions": {"en": "?", "mr": "?"}}]
    jobs = evaluate.plan(items, ["en", "mr"], ["single", "council"],
                         ["native"], do_generate=True)
    assert len(jobs) == 2 * 2 * 2
    assert len({(j[0]["id"], j[1], j[3]) for j in jobs}) == 8


def test_resuming_skips_exactly_what_was_done(tmp_path):
    items = [{"id": "a", "questions": {"en": "?"}},
             {"id": "b", "questions": {"en": "?"}}]
    jobs = evaluate.plan(items, ["en"], ["single", "council"], ["native"], True)

    done = {("a", "en", "-", "single"): {}}
    todo = [j for j in jobs
            if (j[0]["id"], j[1], j[2] or "-", j[3]) not in done]
    assert len(todo) == 3
    assert ("a", "single") not in {(j[0]["id"], j[3]) for j in todo}


# ------------------------------------------------- token accounting
def test_usage_starts_clean_and_can_be_reset():
    answer_writer.reset_tokens()
    assert answer_writer.tokens_used()["total"] == 0


def test_usage_adds_up(monkeypatch):
    answer_writer.reset_tokens()

    class Usage:
        prompt_tokens, completion_tokens, total_tokens = 100, 50, 150

    class Response:
        usage = Usage()

    answer_writer._record_usage(Response())
    answer_writer._record_usage(Response())
    used = answer_writer.tokens_used()
    assert used == {"calls": 2, "prompt": 200, "completion": 100, "total": 300}
    answer_writer.reset_tokens()


def test_a_response_without_usage_does_not_crash():
    answer_writer.reset_tokens()
    answer_writer._record_usage(object())
    assert answer_writer.tokens_used()["calls"] == 1
    answer_writer.reset_tokens()


def test_the_returned_usage_cannot_be_edited_from_outside():
    answer_writer.reset_tokens()
    snapshot = answer_writer.tokens_used()
    snapshot["total"] = 999_999
    assert answer_writer.tokens_used()["total"] == 0


# ------------------------------------------------------------- the CLI
def test_help_documents_the_three_arms():
    result = subprocess.run(
        [sys.executable, "evaluate.py", "--help"],
        cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0
    for word in ("selfcons", "council", "single", "--report", "--budget-tokens"):
        assert word in result.stdout, f"--help does not mention {word}"


def test_report_on_an_empty_log_says_so(tmp_path):
    result = subprocess.run(
        [sys.executable, "evaluate.py", "--report",
         "--out", str(tmp_path / "nothing")],
        cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert result.returncode == 1
    assert "Nothing saved" in result.stdout
