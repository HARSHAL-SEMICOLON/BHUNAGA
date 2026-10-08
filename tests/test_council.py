"""
Tests for the council of experts.

No network anywhere. Every test replaces answer_writer.chat with a plain
function, which is the single door all model calls go through, so we can decide
exactly what each expert "says" and check what the council does with it.

The interesting cases are the ugly ones: a chairman that ignores the JSON
instruction, an expert that rate-limits, everyone abstaining. Those are what
happens on a Friday afternoon on the free tier, and the app has to survive them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from farmer import answer_writer, council
from farmer.council import agreement, chairman, member, roles
from farmer.searcher import RetrievedChunk

CHUNKS = [RetrievedChunk("Wheat needs 50 kg urea per acre.", "icar.md", "en", 0.9)]


@pytest.fixture
def talk(monkeypatch):
    """Give the test a way to script what the model replies."""
    def install(fn):
        monkeypatch.setattr(answer_writer, "chat", fn)
    return install


# ------------------------------ the seats ------------------------------ #
def test_three_seats_with_distinct_jobs():
    assert len(roles.SEATS) == 3
    assert len({s.key for s in roles.SEATS}) == 3
    # if two seats had the same remit there would be no point asking both
    assert len({s.remit for s in roles.SEATS}) == 3


def test_every_seat_is_told_it_may_abstain():
    for seat in roles.SEATS:
        assert roles.ABSTAIN in roles.brief(seat, "Marathi")
        assert "Marathi" in roles.brief(seat, "Marathi")


@pytest.mark.parametrize("said", [
    "NO_INPUT", "NO_INPUT.", "  no_input  ", "**NO_INPUT**",
    "NO_INPUT (nothing here for me)",
])
def test_abstain_is_recognised_however_it_is_written(said):
    """Models rarely return the bare token, so we match on the opening."""
    assert member._looks_like_abstain(said)


@pytest.mark.parametrize("said", [
    "Apply 50 kg urea", "No, that is not in the documents", "input needed",
])
def test_real_answers_are_not_mistaken_for_abstaining(said):
    assert not member._looks_like_abstain(said)


# --------------------------- one expert -------------------------------- #
def test_expert_that_abstains_did_not_speak(talk):
    talk(lambda system, user, **kw: "NO_INPUT")
    op = member.consult(roles.AGRONOMIST, "q", "ctx", "English")
    assert op.abstained and not op.spoke and op.text == ""


def test_expert_failure_is_caught_not_raised(talk):
    def boom(system, user, **kw):
        raise RuntimeError("rate limit reached")
    talk(boom)
    op = member.consult(roles.ECONOMIST, "q", "ctx", "English")
    assert op.failed and not op.spoke and "rate limit" in op.error


def test_transcript_leaves_out_the_quiet_seats():
    ops = [
        member.Opinion(roles.AGRONOMIST, "apply urea"),
        member.Opinion(roles.ECONOMIST, "", abstained=True),
        member.Opinion(roles.SCHEME_OFFICER, "", failed=True, error="x"),
    ]
    text = member.transcript(ops)
    assert "apply urea" in text
    # an empty opinion reads as disagreement to the chairman, so it is dropped
    assert "Farm Economist" not in text and "Scheme Officer" not in text


# --------------------------- the chairman ------------------------------ #
def test_chairman_json_is_parsed():
    parsed = chairman._extract_json(
        '{"answer":"a","agreement":80,"conflicts":[],"basis":"b"}')
    assert parsed["answer"] == "a" and parsed["agreement"] == 80


@pytest.mark.parametrize("wrapped", [
    '```json\n{"answer":"a"}\n```',
    '```\n{"answer":"a"}\n```',
    'Sure, here you go:\n{"answer":"a"}\nHope that helps!',
])
def test_chairman_json_survives_being_wrapped_in_chatter(wrapped):
    assert chairman._extract_json(wrapped)["answer"] == "a"


def test_chairman_prose_returns_none_so_we_can_fall_back():
    assert chairman._extract_json("no json at all here") is None


@pytest.mark.parametrize("given,want", [
    (88, 88), ("88", 88), ("88%", 88), (" 92 ", 92),
    (150, 100), (-5, 0), (None, 50), ("rubbish", 50),
])
def test_agreement_number_is_read_however_it_arrives(given, want):
    assert chairman._as_int(given) == want


def test_conflicts_accepts_a_list_or_a_bare_string():
    assert chairman._as_lines(["a", "b"]) == ["a", "b"]
    assert chairman._as_lines("just one") == ["just one"]
    assert chairman._as_lines(None) == []
    assert chairman._as_lines(["", "  "]) == []


# ------------------------- measuring agreement ------------------------- #
def test_one_opinion_cannot_disagree_with_itself():
    assert agreement.overlap(["only one"]) == 1.0


def test_identical_and_opposite_opinions():
    assert agreement.overlap(["urea fifty kilo acre"] * 2) == 1.0
    assert agreement.overlap(["urea fifty kilo", "subsidy form rupees"]) == 0.0


def test_overlap_works_on_devanagari():
    """The whole app is trilingual; a metric that only handles Latin is useless."""
    assert agreement.overlap(["युरिया पन्नास किलो"] * 2) == 1.0
    assert 0.0 <= agreement.overlap(
        ["कांदा साठवण कोरड्या जागी", "कांदा विक्री बाजारात"]) < 1.0


def test_filler_words_do_not_inflate_agreement():
    """Two answers that share only "the" and "and" have not agreed."""
    assert agreement.overlap(["the urea and the wheat",
                              "the subsidy and the form"]) == 0.0


@pytest.mark.parametrize("score,want", [(90, "strong"), (75, "strong"),
                                        (60, "partial"), (45, "partial"),
                                        (20, "split")])
def test_labels_sit_on_the_configured_thresholds(score, want):
    assert agreement.label(score, config.CONSENSUS_STRONG,
                           config.CONSENSUS_WEAK) == want


def test_blend_stays_in_range_and_follows_both_inputs():
    assert 0 <= agreement.blend(0, 0.0) <= 100
    assert agreement.blend(100, 1.0) == 100
    # the chairman carries more weight, but the measurement still moves it
    assert agreement.blend(90, 1.0) > agreement.blend(90, 0.0)


# ------------------------ the whole council ---------------------------- #
def _panel_says(talk, agro="- urea 50 kg [1]", econ="- costs Rs 300 [1]",
                scheme="NO_INPUT", chair=None):
    chair = chair or ('{"answer":"Apply 50 kg urea.","agreement":85,'
                      '"conflicts":["dose timing"],"basis":"agronomist"}')

    def reply(system, user, **kw):
        if "Chairman" in system:
            return chair
        if "Agronomist" in system:
            return agro
        if "Economist" in system:
            return econ
        return scheme
    talk(reply)


def test_full_round(talk):
    _panel_says(talk)
    result = council.deliberate("q", CHUNKS, "English")
    assert result.verdict.answer == "Apply 50 kg urea."
    assert result.verdict.conflicts == ["dose timing"]
    assert result.verdict.spoke == ["agronomist", "economist"]
    assert result.verdict.quiet == ["scheme_officer"]
    assert 0 <= result.verdict.score <= 100


def test_chairman_prose_is_used_as_the_answer(talk):
    _panel_says(talk, chair="The experts broadly agree: apply urea.")
    v = council.deliberate("q", CHUNKS, "English").verdict
    assert v.fell_back and v.answer == "The experts broadly agree: apply urea."


def test_a_single_speaker_skips_the_chairman(talk):
    calls = []

    def reply(system, user, **kw):
        calls.append(system[:20])
        return "- only agronomy [1]" if "Agronomist" in system else "NO_INPUT"
    talk(reply)

    v = council.deliberate("q", CHUNKS, "English").verdict
    assert len(calls) == 3, "the chairman should not have been paid for"
    assert v.score == 100 and v.spoke == ["agronomist"]


def test_nobody_speaking_raises_so_the_caller_can_fall_back(talk):
    talk(lambda system, user, **kw: "NO_INPUT")
    with pytest.raises(RuntimeError):
        council.deliberate("q", CHUNKS, "English")


def test_context_numbering_matches_the_single_agent_path():
    """[2] has to mean the same chunk in both paths or citations are nonsense."""
    chunks = [RetrievedChunk("a", "one.md", "en", 1.0),
              RetrievedChunk("b", "two.md", "en", 0.9)]
    assert council._format_context(chunks) == answer_writer._format_context(chunks)


# ---------------- how generate() chooses between the two --------------- #
def test_generate_uses_the_council_when_asked(talk):
    _panel_says(talk)
    ans = answer_writer.generate("q", "en", CHUNKS, use_council=True)
    assert ans.council is not None and ans.strategy == "native+council"


def test_generate_skips_the_council_when_told_to(talk, monkeypatch):
    monkeypatch.setattr(answer_writer, "_generate_with_groq",
                        lambda q, c, lang: "plain answer")
    ans = answer_writer.generate("q", "en", CHUNKS, use_council=False)
    assert ans.council is None and ans.text == "plain answer"


def test_a_broken_council_still_answers_the_farmer(talk, monkeypatch):
    """The whole point of the fallback: never show a farmer a stack trace."""
    def boom(system, user, **kw):
        raise RuntimeError("429 rate limit")
    talk(boom)
    monkeypatch.setattr(answer_writer, "_generate_with_groq",
                        lambda q, c, lang: "plain answer")
    ans = answer_writer.generate("q", "en", CHUNKS, use_council=True)
    assert ans.council is None and ans.text == "plain answer"


def test_marathi_translate_after_debates_in_english(talk, monkeypatch):
    """
    Translating three expert opinions nobody reads would cost three more model
    loads, so only the finished answer goes through IndicTrans2.
    """
    seen = []

    def reply(system, user, **kw):
        seen.append(system)
        return ('{"answer":"Apply urea.","agreement":90,"conflicts":[],'
                '"basis":"x"}') if "Chairman" in system else "- urea [1]"
    talk(reply)
    monkeypatch.setattr(answer_writer, "_translate_en_to_mr",
                        lambda t: "युरिया वापरा.")
    monkeypatch.setattr(config, "MARATHI_STRATEGY", "translate_after")

    ans = answer_writer.generate("q", "mr", CHUNKS, use_council=True)
    assert all("English" in s for s in seen)
    assert ans.text == "युरिया वापरा."
    assert ans.strategy == "translate_after+council"


def test_serial_and_parallel_give_the_same_result(talk, monkeypatch):
    _panel_says(talk)
    monkeypatch.setattr(config, "COUNCIL_PARALLEL", False)
    serial = council.deliberate("q", CHUNKS, "English")
    monkeypatch.setattr(config, "COUNCIL_PARALLEL", True)
    parallel = council.deliberate("q", CHUNKS, "English")
    assert serial.verdict.answer == parallel.verdict.answer
    assert serial.verdict.spoke == parallel.verdict.spoke
