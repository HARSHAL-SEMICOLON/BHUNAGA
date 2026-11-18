"""
Things that only break once the app is deployed.

Every test here encodes a failure that does not show up on a development
machine, because the development machine has a .env, a warm model cache and a
working network. A Space has none of those on the morning somebody opens the
link.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _requirements() -> str:
    return (ROOT / "requirements.txt").read_text(encoding="utf-8")


def _space_readme() -> str:
    return (ROOT / "deploy" / "HF_SPACE_README.md").read_text(encoding="utf-8")


def _streamlit_floor() -> tuple[int, int]:
    match = re.search(r"^streamlit>=(\d+)\.(\d+)", _requirements(), re.MULTILINE)
    assert match, "streamlit is not pinned in requirements.txt"
    return int(match.group(1)), int(match.group(2))


# ------------------------------------------------- the Streamlit version
def test_the_pinned_version_supports_what_the_screens_call():
    """
    The screens use width="stretch" (1.50) and st.container(key=) (1.48).
    On anything older the app does not degrade — it raises TypeError on the
    first button it draws, before a single screen renders.
    """
    assert _streamlit_floor() >= (1, 50), (
        f"streamlit>={_streamlit_floor()} is below what ui/ actually calls")


def test_the_space_sdk_version_matches_the_requirement():
    """
    A Space pins its own SDK version in the README front matter and ignores
    requirements.txt for Streamlit itself. If that number is below the floor,
    the deployed app crashes while the local one is fine.
    """
    match = re.search(r"^sdk_version:\s*(\d+)\.(\d+)", _space_readme(),
                      re.MULTILINE)
    assert match, "the Space README has no sdk_version"
    sdk = (int(match.group(1)), int(match.group(2)))
    assert sdk >= _streamlit_floor(), (
        f"Space pins streamlit {sdk}, requirements need {_streamlit_floor()}")


@pytest.mark.parametrize("call,needs", [
    ('width="stretch"', (1, 50)),
    ("st.container(key=", (1, 48)),
    ("st.audio_input", (1, 40)),
])
def test_each_modern_api_is_covered_by_the_pin(call, needs):
    """If a screen uses it, the pin has to be high enough for it."""
    used = any(call in p.read_text(encoding="utf-8")
               for p in (ROOT / "ui").glob("*.py"))
    if used:
        assert _streamlit_floor() >= needs, f"{call} needs streamlit {needs}"


# --------------------------------------------------------------- secrets
def _gitignore() -> str:
    return (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_the_streamlit_secrets_file_is_ignored():
    """
    .streamlit/secrets.toml.example tells you to copy it to secrets.toml and
    fill in real keys. If the copy is not ignored, following the project's own
    instructions commits a live Groq key.
    """
    assert ".streamlit/secrets.toml" in _gitignore()


def test_the_example_secrets_hold_no_real_keys():
    text = (ROOT / ".streamlit" / "secrets.toml.example").read_text(
        encoding="utf-8")
    # a real Groq key is long and starts gsk_; a placeholder is not
    assert "gsk_" not in text
    assert "your-" in text, "the example should obviously be a placeholder"


@pytest.mark.parametrize("name", [".env", "farmer_profile.json",
                                  "places_cache.json", "market_cache.json"])
def test_nothing_personal_is_committed(name):
    assert name in _gitignore()


# ------------------------------------------------------- the shipped index
def test_the_index_ships_with_the_repo():
    """
    A Space has no build step and loses its disk when it sleeps. An index built
    at deploy time would be gone by morning, so it is committed on purpose.
    """
    folder = ROOT / "models" / "local_kb"
    assert (folder / "dense.npy").exists(), "no shipped index"
    assert (folder / "meta.json").exists()
    assert "!models/local_kb/" in _gitignore(), (
        "the index is gitignored, so the Space would wake up empty")


def test_the_shipped_index_is_not_corrupted_by_line_endings():
    """
    Two machines with different autocrlf settings rewrote each other's files.
    A line-ending rewrite inside a float32 array corrupts the vectors silently
    — no error, just wrong answers, and only on the deployed Space.
    """
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "*.npy binary" in attributes

    import numpy as np
    matrix = np.load(ROOT / "models" / "local_kb" / "dense.npy")
    assert matrix.ndim == 2 and matrix.shape[1] == 1024
    assert np.isfinite(matrix).all(), "the shipped index contains NaN or inf"


def test_the_shipped_index_is_multilingual():
    """The whole premise. An English-only index would make the Space monolingual."""
    import json
    meta = json.loads((ROOT / "models" / "local_kb" / "meta.json").read_text(
        encoding="utf-8"))
    langs = {m.get("source_lang") for m in meta}
    assert {"en", "hi", "mr"} <= langs, f"index languages: {langs}"


# -------------------------------------------------- the cold-start message
def test_the_first_load_is_announced_in_every_language():
    """
    Two minutes of "Finding the answer..." while a 2.5 GB model downloads reads
    as a crash. The first question has to say it is a one-time wait.
    """
    from farmer.text import STRINGS
    assert "common.firstload" in STRINGS
    for lang in ("en", "hi", "mr"):
        assert STRINGS["common.firstload"][lang]


def test_the_ask_screen_checks_whether_the_model_is_loaded():
    source = (ROOT / "ui" / "ask.py").read_text(encoding="utf-8")
    assert "is_loaded()" in source and "common.firstload" in source


def test_is_loaded_reports_honestly():
    from farmer import text_embedder
    # nothing has loaded the 2.5 GB model in a test run, and nothing should
    assert text_embedder.is_loaded() is (text_embedder._model is not None)
