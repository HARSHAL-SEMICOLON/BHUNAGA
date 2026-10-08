"""
Tests for the things that were missing.

Each test here corresponds to a gap found in the audit, and exists so the gap
cannot quietly come back. Several of them check facts about the repository
itself — that the knowledge base really is multilingual, that personal data is
ignored by git — because those are exactly the kind of thing that decays without
anyone noticing.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
from farmer import assistant, intent, scoring
from farmer.language_detector import detect

DEVANAGARI = re.compile(r"[ऀ-ॿ]")


# ------------------------------------------- the knowledge base is multilingual
def test_the_corpus_is_genuinely_mixed_language():
    """
    The central claim of the project. It was false: every document was English,
    which left SAME_LANG_BOOST with nothing to boost and made the same_lang
    metric zero by construction for every Hindi and Marathi query.
    """
    langs = {}
    for path in (ROOT / "data").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        langs.setdefault(detect(text[:3000]).lang, []).append(path.name)

    assert "en" in langs, "no English documents"
    assert "hi" in langs, f"no Hindi documents — found {sorted(langs)}"
    assert "mr" in langs, f"no Marathi documents — found {sorted(langs)}"


def test_native_documents_are_substantial_not_token():
    """A two-line Marathi file would satisfy the test above and fool nobody."""
    for path in (ROOT / "data").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if detect(text[:3000]).lang in ("hi", "mr"):
            assert len(DEVANAGARI.findall(text)) > 1000, \
                f"{path.name} is too thin to be a real source document"


def test_same_language_retrieval_is_now_possible():
    """
    For each of hi and mr there has to be at least one document in that
    language, or SAME_LANG_BOOST can never fire.
    """
    by_lang = {}
    for path in (ROOT / "data").glob("*.md"):
        lang = detect(path.read_text(encoding="utf-8")[:3000]).lang
        by_lang[lang] = by_lang.get(lang, 0) + 1
    assert by_lang.get("hi", 0) >= 1 and by_lang.get("mr", 0) >= 1


# --------------------------------------------------------- repository hygiene
def _gitignore() -> str:
    return (ROOT / ".gitignore").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", [
    "farmer_profile.json",      # the farmer's name, village and land size
    "places_cache.json",
    "market_cache.json",
])
def test_personal_and_cache_files_are_ignored(name):
    """
    The old .gitignore said "profile.json"; the file is farmer_profile.json,
    so a real farmer's details were being committed.
    """
    assert name in _gitignore(), f"{name} would be committed"


def test_the_local_index_is_ignored():
    assert "models/local_kb" in _gitignore()


@pytest.mark.parametrize("key", [
    "VECTOR_BACKEND", "COUNCIL_ENABLED", "CHAIRMAN_MODEL",
    "GROQ_API_KEY", "MARATHI_STRATEGY",
])
def test_env_example_documents_every_switch(key):
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert key in text, f"{key} is not in .env.example"


def test_streamlit_floor_is_high_enough_for_the_microphone():
    """
    st.audio_input arrived in Streamlit 1.40. The requirement said 1.36, so a
    clean install produced an app whose voice button silently did not exist.
    """
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    match = re.search(r"streamlit>=(\d+)\.(\d+)", requirements)
    assert match, "streamlit is not pinned"
    major, minor = int(match.group(1)), int(match.group(2))
    assert (major, minor) >= (1, 40), f"streamlit>={major}.{minor} is too old"


# ------------------------------------------------------- the evaluation set
def _questions():
    return json.loads((ROOT / "eval" / "questions.json").read_text(
        encoding="utf-8"))["items"]


def test_every_eval_question_exists_in_all_three_languages():
    for item in _questions():
        for lang in ("en", "hi", "mr"):
            assert item["questions"].get(lang), f"{item['id']} missing {lang}"


def test_every_eval_question_names_a_real_document():
    """expected_source used to be blank on every item, so source_match was dead."""
    names = [p.name for p in (ROOT / "data").glob("*.md")]
    for item in _questions():
        source = item["expected_source"]
        assert source, f"{item['id']} has no expected_source"
        assert any(source.lower() in n.lower() for n in names), \
            f"{item['id']}: expected_source {source!r} matches no file"


def test_every_eval_question_is_answerable_from_that_document():
    """A question the corpus cannot answer measures the harness, not the app."""
    def norm(s):
        return " ".join(unicodedata.normalize("NFKC", s).casefold().split())

    files = {p.name: norm(p.read_text(encoding="utf-8"))
             for p in (ROOT / "data").glob("*.md")}
    for item in _questions():
        blob = " ".join(text for name, text in files.items()
                        if item["expected_source"].lower() in name.lower())
        found = [k for k in item["answer_keywords"] if norm(k) in blob]
        assert found, f"{item['id']}: no keyword appears in its own source"


def test_the_placeholder_comment_is_gone():
    text = (ROOT / "eval" / "questions.json").read_text(encoding="utf-8")
    assert "Replace these with questions grounded in YOUR documents" not in text


def test_the_eval_set_covers_the_native_language_documents():
    sources = {item["expected_source"].lower() for item in _questions()}
    assert any("kanda" in s or "gandulkhat" in s or "yojana" in s
               for s in sources), "nothing tests the Marathi/Hindi documents"


# ---------------------------------------------------- grounding / hallucination
def test_grounding_catches_an_invented_number():
    """The metric that makes the council claim measurable."""
    class Chunk:
        text = "Apply 50 kg urea per acre for wheat."

    assert scoring.score_grounding("Apply 50 kg urea per acre.", [Chunk()]) == 1.0
    assert scoring.score_grounding("Apply 95 kg urea per acre.", [Chunk()]) == 0.0


def test_grounding_ignores_devanagari_digits():
    """५० and 50 are the same number; scoring them apart would be wrong."""
    class Chunk:
        text = "Apply 50 kg urea per acre."

    assert scoring.score_grounding("प्रति एकर ५० किलो युरिया.", [Chunk()]) == 1.0


def test_an_answer_with_no_numbers_is_fully_grounded():
    """Nothing was claimed, so nothing was invented."""
    class Chunk:
        text = "Keep the soil moist."

    assert scoring.score_grounding("Keep the soil moist.", [Chunk()]) == 1.0


def test_grounding_ignores_trivial_numbers():
    class Chunk:
        text = "Water the crop."

    # "2" and "3" carry no factual weight and would only add noise
    assert scoring.score_grounding("Water 2 or 3 times.", [Chunk()]) == 1.0


def test_partial_grounding_is_reported_as_a_fraction():
    class Chunk:
        text = "Apply 50 kg urea and 20 kg potash."

    score = scoring.score_grounding("Use 50 kg urea and 99 kg potash.", [Chunk()])
    assert score == 0.5


def test_answer_keyword_recall():
    assert scoring.score_answer_keywords("apply urea at 50 kg",
                                         ["urea", "50"]) == 1.0
    assert scoring.score_answer_keywords("apply urea", ["urea", "50"]) == 0.5
    assert scoring.score_answer_keywords("nothing", []) == 0.0


# --------------------------------------------------------------- intent
@pytest.mark.parametrize("question,expect", [
    ("What is the price of onion today?", intent.PRICE),
    ("आज कांद्याचा भाव काय आहे?", intent.PRICE),
    ("आज प्याज़ का मंडी भाव क्या है?", intent.PRICE),
    ("Will it rain tomorrow?", intent.WEATHER),
    ("उद्या पाऊस पडेल का?", intent.WEATHER),
    ("कल बारिश होगी क्या?", intent.WEATHER),
    ("When should I spray for bollworm?", intent.SPRAY),
    ("फवारणी कधी करावी?", intent.SPRAY),
    ("Am I eligible for PM-Kisan?", intent.SCHEME),
    ("मी पीएम-किसानसाठी पात्र आहे का?", intent.SCHEME),
    ("क्या मुझे सब्सिडी मिलेगी?", intent.SCHEME),
    ("How much urea per acre for wheat?", intent.ADVICE),
    ("गव्हासाठी किती युरिया लागते?", intent.ADVICE),
])
def test_intent_is_classified_across_languages(question, expect):
    assert intent.classify(question).name == expect


def test_live_data_questions_are_not_sent_to_the_documents():
    """
    The point of intent detection. A price question answered from a storage
    guide would be confidently, uselessly wrong.
    """
    assert not intent.classify("what is the rate of onion").needs_documents
    assert not intent.classify("will it rain this week").needs_documents
    assert intent.classify("how much urea for wheat").needs_documents


def test_a_price_question_is_pointed_at_the_market_screen():
    assert intent.classify("onion price today").screen == "market"
    for lang in ("en", "hi", "mr"):
        assert intent.redirect_note(intent.classify("onion price"), lang)


def test_word_boundaries_stop_false_matches():
    """"rate" must not match "generated"; that is why Latin uses boundaries."""
    assert intent.classify("the generated report").name == intent.ADVICE


def test_empty_question_defaults_to_advice():
    assert intent.classify("").name == intent.ADVICE
    assert intent.classify("   ").name == intent.ADVICE


# ------------------------------------------------- the channel-agnostic core
class _Reply:
    """A Reply built by hand, so the formatters can be tested on their own."""
    def __new__(cls, **kw):
        base = dict(text="Apply 50 kg urea per acre [1].", lang="en",
                    intent="advice", redirect="", sources=[], consensus=None,
                    experts=0, error="")
        base.update(kw)
        return assistant.Reply(**base)


def test_text_channel_names_its_sources():
    """A farmer acting on advice should be able to say where it came from."""
    out = assistant.for_text_channel(
        _Reply(sources=[{"source": "wheat.md", "lang": "en"}]))
    assert "wheat.md" in out


def test_text_channel_warns_when_the_experts_disagreed():
    """On a phone there is no panel to expand, so it has to be said in words."""
    out = assistant.for_text_channel(_Reply(consensus=20))
    assert "did not fully agree" in out


def test_text_channel_stays_silent_when_they_agreed():
    assert "did not fully agree" not in assistant.for_text_channel(
        _Reply(consensus=95))


def test_text_channel_respects_the_whatsapp_limit():
    out = assistant.for_text_channel(_Reply(text="x" * 5000), max_chars=1500)
    assert len(out) <= 1500


def test_voice_channel_strips_what_cannot_be_spoken():
    """Citation markers and bullets are meaningless read out loud."""
    spoken = assistant.for_voice_channel(
        _Reply(text="- Apply **50 kg** urea [1].\n- Water after [2]."))
    assert "[1]" not in spoken and "**" not in spoken and "\n" not in spoken


def test_voice_channel_shortens_a_long_answer():
    long_answer = "This is a sentence about urea. " * 80
    spoken = assistant.for_voice_channel(_Reply(text=long_answer))
    assert len(spoken) < len(long_answer)
    assert "call again" in spoken


def test_a_failed_reply_still_says_something_usable():
    assert assistant.for_voice_channel(_Reply(text="", error="boom"))
    assert assistant.for_text_channel(_Reply(text="", error="boom"))


def test_assistant_rejects_an_empty_question():
    reply = assistant.ask("")
    assert not reply.ok and reply.error


# ------------------------------------------------------ WhatsApp / IVR webhook
def test_whatsapp_greeting_is_returned_for_hello(monkeypatch):
    from channels import webhook

    def boom(*a, **k):
        raise AssertionError("a greeting must not cost a model call")
    monkeypatch.setattr(webhook.assistant, "ask", boom)

    for greeting in ("hi", "Hello", "नमस्कार", ""):
        out = webhook.handle_whatsapp(greeting)
        assert "Bhunaga" in out and "<Message>" in out


def test_whatsapp_answers_a_real_question(monkeypatch):
    from channels import webhook
    monkeypatch.setattr(webhook.assistant, "ask",
                        lambda q, **k: _Reply(text="Apply 50 kg urea."))
    out = webhook.handle_whatsapp("how much urea for wheat")
    assert "Apply 50 kg urea." in out


def test_twiml_escapes_special_characters(monkeypatch):
    """An unescaped & or < in an answer produces XML Twilio will reject."""
    from channels import webhook
    monkeypatch.setattr(webhook.assistant, "ask",
                        lambda q, **k: _Reply(text="cost < 500 & rising"))
    out = webhook.handle_whatsapp("cost?")
    assert "&lt;" in out and "&amp;" in out
    assert "< 500" not in out


def test_voice_call_records_the_question():
    from channels import webhook
    out = webhook.handle_voice_start()
    assert "<Record" in out and 'action="/voice/reply"' in out
    assert "maxLength" in out, "an unbounded recording can hang the call"


def test_voice_reply_reads_the_answer_back(monkeypatch):
    from channels import webhook
    monkeypatch.setattr(webhook.voice, "transcribe",
                        lambda *a, **k: webhook.voice.Heard(
                            text="how much urea", lang="mr"))
    monkeypatch.setattr(webhook.assistant, "ask",
                        lambda q, **k: _Reply(text="Apply 50 kg.", lang="mr"))
    out = webhook.handle_voice_reply(b"fake audio")
    assert "<Say" in out and "Apply 50 kg." in out


def test_voice_reply_handles_an_unintelligible_recording(monkeypatch):
    from channels import webhook
    monkeypatch.setattr(webhook.voice, "transcribe",
                        lambda *a, **k: webhook.voice.Heard(
                            text="", error="too short"))
    out = webhook.handle_voice_reply(b"")
    assert "could not hear" in out
