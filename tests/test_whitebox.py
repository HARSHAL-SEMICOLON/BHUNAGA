"""
Tests that look inside the code and check each small part.

We check: cutting text into pieces, finding the language, the score maths,
the search language-bonus, and how the answer picks Marathi vs English.
Run: pytest tests/test_whitebox.py -v
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import ingest
from farmer import answer_writer, language_detector, scoring, searcher, vector_database


# cutting text into pieces
def test_chunk_empty_returns_nothing():
    assert ingest.chunk_text("") == []
    assert ingest.chunk_text("   \n\t ") == []


def test_chunk_shorter_than_size_is_single_chunk():
    assert ingest.chunk_text("short text") == ["short text"]


def test_chunk_collapses_whitespace():
    assert ingest.chunk_text("a   b\n\nc\t d") == ["a b c d"]


def test_chunk_overlap_and_coverage():
    text = "x" * 2000
    chunks = ingest.chunk_text(text)
    assert len(chunks) >= 2
    assert len(chunks[0]) == config.CHUNK_SIZE
    step = config.CHUNK_SIZE - config.CHUNK_OVERLAP
    assert len("".join(c[: step if i < len(chunks) - 1 else len(c)]
                       for i, c in enumerate(chunks))) == len(text)


# finding the language with the real lingua tool
def test_langid_empty_text_is_default():
    r = language_detector.detect("   ")
    assert r.lang == config.DEFAULT_LANG and r.confidence == 0.0


def test_langid_detects_english():
    r = language_detector.detect("How much urea per acre is recommended for wheat crop?")
    assert r.lang == "en"


def test_langid_separates_hindi_from_marathi():
    hi = language_detector.detect("शहर में बारिश हो रही है और खेत में पानी भर गया है")
    mr = language_detector.detect("शहरात पाउस पडत आहे आणि शेतात पाणी साचले आहे")
    assert hi.lang == "hi"
    assert mr.lang == "mr"


def test_langid_low_confidence_falls_back(monkeypatch):
    monkeypatch.setattr(config, "LANGID_MIN_CONFIDENCE", 1.1)
    r = language_detector.detect("गव्हासाठी युरिया")
    assert r.lang == config.DEFAULT_LANG
    assert r.raw_lang in config.SUPPORTED_LANGS


# the scoring maths
@dataclass
class _C:
    text: str
    source: str
    source_lang: str
    score: float = 0.0


def test_norm_and_contains_cross_script_and_case():
    assert scoring._contains("Apply UREA now", "urea")
    assert scoring._contains("प्रति एकर युरिया द्या",
                             "युरिया")
    assert not scoring._contains("only cotton here", "urea")


def test_score_empty_keywords_no_division_error():
    s = scoring.score_retrieval([_C("anything", "s.pdf", "en")], [], "en")
    assert s.keyword_recall == 0.0 and s.hit_at_k == 0


def test_score_keyword_recall_and_first_hit_rr_rank():
    chunks = [
        _C("irrelevant cotton", "a.pdf", "en"),
        _C("apply urea 50 kg", "b.pdf", "en"),
    ]
    s = scoring.score_retrieval(chunks, ["urea", "kg", "missingword"], "en")
    assert s.hit_at_k == 1
    assert s.keyword_recall == 0.667
    assert s.first_hit_rr == 0.5


def test_score_same_lang_ratio_and_source_match():
    chunks = [_C("t", "icar_wheat.pdf", "en"), _C("t", "x.pdf", "mr")]
    s = scoring.score_retrieval(chunks, ["t"], "en", expected_source="icar_wheat")
    assert s.same_lang_ratio == 0.5
    assert s.source_match == 1
    s2 = scoring.score_retrieval(chunks, ["t"], "en", expected_source="absent")
    assert s2.source_match == 0


def test_score_language_uses_detector():
    hi_text = "शहर में बारिश हो रही है और खेत में पानी भर गया"
    assert scoring.score_language(hi_text, "hi") == 1
    assert scoring.score_language(hi_text, "mr") == 0


def test_aggregate_means_numeric_only():
    rows = [{"a": 1.0, "b": 0, "txt": "x"}, {"a": 3.0, "b": 1, "txt": "y"}]
    assert scoring.aggregate(rows) == {"a": 2.0, "b": 0.5}


# the vector database helpers
def test_to_sparse_vector_indices_values_align():
    sv = vector_database.to_sparse_vector({3: 0.5, 7: 0.9})
    assert list(sv.indices) == [3, 7]
    assert list(sv.values) == [0.5, 0.9]


def test_build_point_has_named_dense_and_sparse():
    p = vector_database.build_point("id1", [0.0] * 4, {1: 1.0}, {"text": "t"})
    assert config.DENSE_VECTOR_NAME in p.vector
    assert config.SPARSE_VECTOR_NAME in p.vector
    assert p.payload["text"] == "t"


# search: the same-language bonus, using an in-memory store
def _wire_inmemory(monkeypatch):
    from qdrant_client import QdrantClient
    import uuid
    from farmer import text_embedder

    client = QdrantClient(location=":memory:")
    vector_database.ensure_collection(client, recreate=True)
    dense = [1.0, 0.0, 0.0] + [0.0] * (config.EMBED_DIM - 3)
    pts = [
        vector_database.build_point(str(uuid.uuid4()), dense, {1: 1.0},
                          {"text": "urea en", "source": "en.pdf", "source_lang": "en"}),
        vector_database.build_point(str(uuid.uuid4()), dense, {1: 1.0},
                          {"text": "urea mr", "source": "mr.pdf", "source_lang": "mr"}),
    ]
    client.upsert(collection_name=config.QDRANT_COLLECTION, points=pts)
    monkeypatch.setattr(vector_database, "get_client", lambda: client)
    monkeypatch.setattr(text_embedder, "embed_query",
                        lambda q: text_embedder.Embedding(dense=dense, sparse={1: 1.0}))


def test_same_lang_boost_on_promotes_query_language(monkeypatch):
    _wire_inmemory(monkeypatch)
    monkeypatch.setattr(config, "SAME_LANG_BOOST", 0.5)
    res = searcher.retrieve("urea", "mr", top_k=2)
    assert res[0].source_lang == "mr"


def test_same_lang_boost_off_does_not_crash_and_returns_k(monkeypatch):
    _wire_inmemory(monkeypatch)
    monkeypatch.setattr(config, "SAME_LANG_BOOST", 0.0)
    res = searcher.retrieve("urea", "mr", top_k=2)
    assert len(res) == 2


# answer: choosing Marathi-direct vs translate, without calling the real AI
def _stub_generation(monkeypatch):
    monkeypatch.setattr(answer_writer, "_generate_with_groq",
                        lambda q, c, lang_name: f"[groq:{lang_name}] answer")
    monkeypatch.setattr(answer_writer, "_translate_en_to_mr",
                        lambda text: "[translated->mr] " + text)


def test_english_always_native(monkeypatch):
    _stub_generation(monkeypatch)
    monkeypatch.setattr(config, "MARATHI_STRATEGY", "translate_after")
    ans = answer_writer.generate("q", "en", [])
    assert ans.strategy == "native" and "groq:English" in ans.text


def test_hindi_always_native_even_if_translate_flag(monkeypatch):
    _stub_generation(monkeypatch)
    monkeypatch.setattr(config, "MARATHI_STRATEGY", "translate_after")
    ans = answer_writer.generate("q", "hi", [])
    assert ans.strategy == "native" and "groq:Hindi" in ans.text


def test_marathi_native_strategy(monkeypatch):
    _stub_generation(monkeypatch)
    monkeypatch.setattr(config, "MARATHI_STRATEGY", "native")
    ans = answer_writer.generate("q", "mr", [])
    assert ans.strategy == "native" and "groq:Marathi" in ans.text


def test_marathi_translate_after_strategy(monkeypatch):
    _stub_generation(monkeypatch)
    monkeypatch.setattr(config, "MARATHI_STRATEGY", "translate_after")
    ans = answer_writer.generate("q", "mr", [])
    assert ans.strategy == "translate_after"
    assert ans.text.startswith("[translated->mr]")
    assert "groq:English" in ans.text
