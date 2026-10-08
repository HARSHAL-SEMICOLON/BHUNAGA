"""
A full run of the search part, with no internet and no big model.

We use Qdrant in memory (no Docker) and a small fake "embedder" that gives the
same vector to the same topic in any language. This lets us check that a
question in one language can find a document in another language, and that the
same-language bonus works.

Run: python tests/test_integration.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

# make the project importable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from farmer import text_embedder, scoring, searcher, vector_database
from qdrant_client import QdrantClient

# a fake embedder: same topic gives the same vector in any language
TOPICS = {
    "urea":   ["urea", "यूरिया", "युरिया", "fertilizer", "खत", "खाद"],
    "cotton": ["cotton", "कपास", "कापूस", "sowing", "बुवाई", "पेरणी"],
    "blight": ["blight", "झुलसा", "करपा", "tomato", "टमाटर", "टोमॅटो"],
}
TOPIC_IDS = {name: i for i, name in enumerate(TOPICS)}


def _topic_of(text: str) -> str:
    t = text.lower()
    best, best_hits = "urea", -1
    for name, words in TOPICS.items():
        hits = sum(1 for w in words if w.lower() in t)
        if hits > best_hits:
            best, best_hits = name, hits
    return best


def _fake_embedding(text: str) -> text_embedder.Embedding:
    # one number per topic, so the same topic matches across languages
    dense = [0.0] * config.EMBED_DIM
    dense[TOPIC_IDS[_topic_of(text)]] = 1.0
    # turn each word into a number, to also match exact words
    sparse: dict[int, float] = {}
    for tok in text.lower().split():
        sparse[abs(hash(tok)) % 100000] = 1.0
    return text_embedder.Embedding(dense=dense, sparse=sparse)


# test documents: same topics written in different languages
CORPUS = [
    ("Apply 50 kg urea per acre for wheat at sowing time.", "en", "icar_wheat_en.pdf"),
    ("गव्हासाठी पेरणीच्या वेळी प्रति एकर ५० किलो युरिया द्या.", "mr", "krishi_mr.pdf"),
    ("गेहूं के लिए बुवाई के समय प्रति एकड़ ५० किलो यूरिया डालें.", "hi", "krishi_hi.pdf"),
    ("Sow cotton in May-June after the first monsoon showers.", "en", "cotton_en.pdf"),
    ("टोमॅटोमधील करपा रोगासाठी बुरशीनाशकाची फवारणी करा.", "mr", "tomato_mr.pdf"),
]


def build_inmemory_store() -> QdrantClient:
    client = QdrantClient(location=":memory:")
    vector_database.ensure_collection(client, recreate=True)
    points = []
    import uuid
    for text, lang, src in CORPUS:
        emb = _fake_embedding(text)
        points.append(vector_database.build_point(
            point_id=str(uuid.uuid4()),
            dense=emb.dense, sparse=emb.sparse,
            payload={"text": text, "source": src, "source_lang": lang},
        ))
    client.upsert(collection_name=config.QDRANT_COLLECTION, points=points)
    return client


def main():
    # swap the heavy parts for our fakes so we need no model or server
    shared = build_inmemory_store()
    vector_database.get_client = lambda: shared          # search uses this
    text_embedder.embed_query = _fake_embedding          # no big model needed
    config.SAME_LANG_BOOST = 0.10

    failures = 0

    # 1) ask in English -> should find urea text in all languages
    print("\n[T1] cross-language retrieval: English 'urea' query")
    res = searcher.retrieve("how much urea fertilizer for wheat", "en", top_k=3)
    for c in res:
        print(f"     {c.score:.3f} {c.source_lang} {c.source}: {c.text[:38]}...")
    # the top two results should be about urea and in two languages
    top2 = res[:2]
    top2_langs = {c.source_lang for c in top2}
    assert all(_topic_of(c.text) == "urea" for c in top2), "top-2 not on-topic"
    assert len(top2_langs) >= 2, f"expected multilingual top-2, got {top2_langs}"
    print(f"     -> top-2 languages: {sorted(top2_langs)}  [PASS]")

    # 2) ask in Marathi -> should also reach the English document
    print("\n[T2] cross-language retrieval: Marathi 'urea' query -> English doc")
    res = searcher.retrieve("गव्हासाठी किती युरिया खत", "mr", top_k=3)
    assert any(c.source_lang == "en" for c in res), "did not retrieve across to English"
    print(f"     -> reached languages: {sorted({c.source_lang for c in res})}  [PASS]")

    # 3) language bonus: a Marathi question should put Marathi text on top
    print("\n[T3] same-language boost orders same-lang chunk first")
    top = res[0]
    print(f"     top = {top.source_lang} ({top.score:.3f}) {top.source}")
    assert top.source_lang == "mr", f"expected mr on top, got {top.source_lang}"
    print("     -> [PASS]")

    # 4) the scoring works across different scripts
    print("\n[T4] metric scoring across scripts")
    s = scoring.score_retrieval(res, ["urea", "यूरिया", "युरिया", "किलो"], "mr")
    print(f"     {scoring.score_to_dict(s)}")
    assert s.hit_at_k == 1 and s.keyword_recall > 0, "keyword grading failed"
    assert s.same_lang_ratio > 0, "same-lang ratio miscomputed"
    print("     -> [PASS]")

    print("\nALL INTEGRATION TESTS PASSED")
    return failures


if __name__ == "__main__":
    sys.exit(main())
