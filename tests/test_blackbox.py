"""
Tests that use the programs the way a user would, from the command line.

We do not look inside the code. We just run the scripts and check what they
print, the exit code, and the files they make.
Run: pytest tests/test_blackbox.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(args, **kw):
    """Invoke a project script as a user would; capture stdout/stderr/exit."""
    return subprocess.run([sys.executable, *args], cwd=ROOT,
                          capture_output=True, text=True, **kw)


# query.py CLI contract
def test_query_no_args_errors_with_usage():
    r = run(["query.py"])
    assert r.returncode != 0                       # argparse error
    assert "usage" in (r.stderr + r.stdout).lower()


def test_query_help_exits_zero_and_documents_languages():
    r = run(["query.py", "--help"])
    assert r.returncode == 0
    out = r.stdout.lower()
    assert "--interactive" in out and "--show-context" in out


# ingest.py file-handling behavior (no Qdrant needed: returns before connecting)
def test_ingest_empty_directory_is_graceful(tmp_path):
    r = run(["ingest.py", "--path", str(tmp_path)])
    assert r.returncode == 0
    assert "no supported documents" in r.stdout.lower()


def test_ingest_directory_with_only_unsupported_files(tmp_path):
    (tmp_path / "image.png").write_bytes(b"\x89PNG fake")
    (tmp_path / "notes.xyz").write_text("nope")
    r = run(["ingest.py", "--path", str(tmp_path)])
    assert r.returncode == 0
    assert "no supported documents" in r.stdout.lower()


# evaluate.py argument contract
def test_evaluate_rejects_unknown_language():
    r = run(["evaluate.py", "--langs", "xx", "--no-generate"])
    assert r.returncode != 0
    assert "invalid choice" in (r.stderr + r.stdout).lower()


def test_evaluate_help_lists_strategies():
    r = run(["evaluate.py", "--help"])
    assert r.returncode == 0
    assert "translate_after" in r.stdout and "--no-generate" in r.stdout


# Published data contract: questions.json shape other tools rely on
def test_questions_file_contract():
    data = json.loads((ROOT / "eval" / "questions.json").read_text(encoding="utf-8"))
    assert "items" in data and len(data["items"]) >= 1
    for item in data["items"]:
        assert {"id", "questions", "answer_keywords"} <= set(item)
        # every item carries all three languages in parallel
        assert set(item["questions"]) == {"en", "hi", "mr"}
        assert all(item["questions"][l].strip() for l in ("en", "hi", "mr"))
        assert isinstance(item["answer_keywords"], list) and item["answer_keywords"]


# requirements.txt contract: the free stack is actually declared
def test_requirements_declares_free_stack():
    req = (ROOT / "requirements.txt").read_text().lower()
    for pkg in ("qdrant-client", "flagembedding", "lingua-language-detector", "groq"):
        assert pkg in req, f"{pkg} missing from requirements.txt"
