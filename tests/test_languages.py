"""
Does the site really work in all three languages?

It is easy to ship a "trilingual" app where the answers are translated and every
button still says Calculate. These tests exist to stop that: they assert that
every string has all three translations, that no screen hard-codes English, and
that switching the profile language actually changes what is drawn.

The last one is the only test that catches a screen someone forgot to wire up.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from farmer import text as strings
from farmer.text import t


# ------------------------------------------------------- the strings table
def test_nothing_is_left_untranslated():
    """
    The whole point of the app. A gap here means a farmer meets English.
    """
    gaps = strings.missing()
    assert not gaps, f"missing translations: {gaps}"


def test_all_three_languages_are_present():
    assert set(strings.LANGS) == {"en", "hi", "mr"}
    for lang in strings.LANGS:
        assert strings.LANG_NAMES[lang]


def test_hindi_and_marathi_are_actually_devanagari():
    """
    Guards against a copy-paste that leaves English text in the Hindi column.
    A handful of entries are emoji or symbols only, so we check the ones with
    real letters in them.
    """
    latin = re.compile(r"[a-zA-Z]{4,}")
    devanagari = re.compile(r"[ऀ-ॿ]")
    suspects = []
    for key, entry in strings.STRINGS.items():
        for lang in ("hi", "mr"):
            value = entry[lang]
            if latin.search(value) and not devanagari.search(value):
                suspects.append(f"{key}[{lang}] = {value!r}")
    assert not suspects, f"look like untranslated English: {suspects}"


def test_unknown_key_returns_the_key_so_it_is_visible():
    """Silently returning "" would hide the mistake behind an empty label."""
    assert t("no.such.key", "en") == "no.such.key"


def test_unknown_language_falls_back_to_english():
    assert t("nav.home", "fr") == t("nav.home", "en")


@pytest.mark.parametrize("given,want", [
    ("mr", "mr"), ("hi", "hi"), ("en", "en"),
    ("auto", "en"), ("", "en"), ("fr", "en"), (None, "en"),
])
def test_resolve_turns_a_profile_setting_into_a_real_language(given, want):
    assert strings.resolve(given) == want


# ------------------------------------------- no screen hard-codes English
UI_DIR = ROOT / "ui"

# strings that are allowed to stay in one language: CSS, HTML, keys, urls,
# names, and the developer-facing help text in the sidebar
ALLOWED = re.compile(
    r"unsafe_allow_html|class=|<div|<span|</|st\.markdown\(f?['\"]<|"
    r"http|key=|format_func|help=|caption|#|import|None|True|False"
)


def test_every_ui_module_uses_the_translation_layer():
    """
    A screen that never imports t() is a screen that is still in English.
    """
    skipped = {"__init__.py", "theme.py"}      # theme is pure CSS
    for path in sorted(UI_DIR.glob("*.py")):
        if path.name in skipped:
            continue
        source = path.read_text(encoding="utf-8")
        assert "from farmer.text import t" in source or "text import" in source, \
            f"{path.name} does not use the translation layer"


def test_no_screen_still_holds_its_own_translation_table():
    """
    Translations used to be scattered through the screens. They live in
    farmer/text.py now, and a second copy would drift out of step with it.
    """
    for path in sorted(UI_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert not re.search(r'"hi"\s*:\s*\{', source), \
            f"{path.name} looks like it has its own translation table"


# ------------------------------------------------- the app in each language
APP = str(ROOT / "app.py")


def _profile(lang):
    from farmer.farmer_profile import Profile
    return Profile(name="", village="Nashik", district="Nashik", crops=[],
                   soil="", land_acres=1.0, language=lang)


def _run(lang, screen_icon=None):
    from streamlit.testing.v1 import AppTest
    import config
    config.VECTOR_BACKEND = "local"
    config.GROQ_API_KEY = ""

    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["profile"] = _profile(lang)
    at.run()
    if screen_icon:
        target = [b for b in at.button if b.label.startswith(screen_icon)]
        assert target, f"no button starting {screen_icon}"
        target[0].click().run()
    return at


def _visible(at) -> str:
    return " ".join([b.label for b in at.button]
                    + [m.value for m in at.markdown])


@pytest.mark.parametrize("lang,expect", [
    ("en", "Home"), ("hi", "होम"), ("mr", "घर"),
])
def test_navigation_is_in_the_farmers_language(lang, expect):
    assert expect in _visible(_run(lang))


@pytest.mark.parametrize("lang,expect", [
    ("en", "Ask a question"), ("hi", "सवाल पूछें"), ("mr", "प्रश्न विचारा"),
])
def test_home_tiles_are_translated(lang, expect):
    assert expect in _visible(_run(lang))


@pytest.mark.parametrize("icon,lang,expect", [
    ("💬", "mr", "तुमचा प्रश्न विचारा"),
    ("💬", "hi", "अपना सवाल पूछें"),
    ("🌅", "mr", "आज मी काय करावे"),
    ("🌅", "hi", "आज मुझे क्या करना चाहिए"),
    ("💰", "mr", "खर्च आणि नफा"),
    ("💰", "hi", "लागत और मुनाफ़ा"),
    ("📈", "mr", "बाजार भाव"),
    ("📈", "hi", "मंडी भाव"),
])
def test_every_screen_is_translated(icon, lang, expect):
    """One case per screen per language — this is what catches a missed screen."""
    at = _run(lang, icon)
    assert not at.exception, [e.message for e in at.exception]
    assert expect in _visible(at), f"{icon} in {lang} did not show {expect!r}"


@pytest.mark.parametrize("lang", ["en", "hi", "mr"])
def test_no_screen_crashes_in_any_language(lang):
    for icon in ("💬", "🌅", "💰", "📈"):
        at = _run(lang, icon)
        assert not at.exception, f"{icon} in {lang}: " \
                                 f"{[e.message for e in at.exception]}"


def test_the_language_switch_is_reachable_without_reading():
    """
    It sits outside the profile form on purpose. Inside the form the choice
    would not apply until the farmer found and pressed Save — a lot to ask of
    someone who cannot read the form.
    """
    at = _run("en")
    labels = [str(r.options) for r in at.radio]
    assert any("मराठी" in o and "हिंदी" in o for o in labels), \
        "the language picker should show the languages in their own script"
