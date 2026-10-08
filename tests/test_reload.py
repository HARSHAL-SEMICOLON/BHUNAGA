"""
Loading the sample knowledge base twice must not duplicate it.

Found by running the app: a stale index of 22 chunks was sitting in
models/local_kb from an earlier partial run, and pressing "Load sample KB"
would have added the full corpus on top of it rather than replacing it.

Duplicated chunks are not a cosmetic problem. Retrieval returns the top k, so a
document present twice takes two of those k slots and crowds out a document
present once — the index quietly starts preferring whatever was loaded most
often.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
from farmer import vector_database
from farmer.local_store import LocalStore


def _points(n: int, source: str):
    return [vector_database.build_point(
        point_id=f"{source}-{i}",
        dense=np.eye(config.EMBED_DIM, dtype=np.float32)[i % config.EMBED_DIM].tolist(),
        sparse={i: 1.0},
        payload={"text": f"chunk {i}", "source": source, "source_lang": "en"})
        for i in range(n)]


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EMBED_DIM", 8)
    s = LocalStore(tmp_path / "kb")
    vector_database.ensure_collection(s)
    return s


def test_recreate_replaces_instead_of_appending(store):
    store.upsert(config.QDRANT_COLLECTION, _points(5, "first.md"))
    assert store.count(config.QDRANT_COLLECTION).count == 5

    # a second load, the way the sidebar now does it
    vector_database.ensure_collection(store, recreate=True)
    store.upsert(config.QDRANT_COLLECTION, _points(5, "first.md"))
    assert store.count(config.QDRANT_COLLECTION).count == 5, \
        "loading the same documents twice doubled the index"


def test_without_recreate_it_would_have_doubled(store):
    """Shows the bug this guards against is real, not hypothetical."""
    store.upsert(config.QDRANT_COLLECTION, _points(5, "first.md"))
    vector_database.ensure_collection(store, recreate=False)
    store.upsert(config.QDRANT_COLLECTION, _points(5, "first.md"))
    assert store.count(config.QDRANT_COLLECTION).count == 10


def test_recreate_clears_the_files_on_disk(store, tmp_path):
    store.upsert(config.QDRANT_COLLECTION, _points(3, "a.md"))
    vector_database.ensure_collection(store, recreate=True)
    assert LocalStore(tmp_path / "kb").count(config.QDRANT_COLLECTION).count == 0


def test_the_sidebar_rebuilds_on_the_first_file_only(monkeypatch):
    """
    The loop must rebuild once and then append, not rebuild every time —
    rebuilding on every file would leave only the last document indexed.
    """
    from ui import sidebar

    calls = []
    monkeypatch.setattr(sidebar.ingest_mod, "load_text", lambda p: "some text")
    monkeypatch.setattr(sidebar.ingest_mod, "chunk_text", lambda t: ["chunk"])
    monkeypatch.setattr(sidebar.text_embedder, "embed_texts",
                        lambda ts: [type("E", (), {"dense": [0.0], "sparse": {}})()
                                    for _ in ts])
    monkeypatch.setattr(sidebar.language_detector, "detect",
                        lambda t: type("L", (), {"lang": "en"})())
    monkeypatch.setattr(sidebar.vector_database, "get_client",
                        lambda: type("C", (), {"upsert": lambda *a, **k: None})())
    monkeypatch.setattr(sidebar.vector_database, "ensure_collection",
                        lambda c, recreate=False: calls.append(recreate))

    for i, name in enumerate(["a.md", "b.md", "c.md"], 1):
        sidebar._ingest_file(Path(name), rebuild=(i == 1))

    assert calls == [True, False, False], calls
