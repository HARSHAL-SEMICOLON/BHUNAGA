"""
Search the saved documents.

It looks using both the meaning vector and the exact-word vector, then joins the
two result lists. It can also give a small bonus to documents that are in the
same language as the question. If nothing is saved yet, it returns an empty list
instead of crashing.
"""

from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import models

import config
from farmer import text_embedder, vector_database


@dataclass
class RetrievedChunk:
    text: str
    source: str
    source_lang: str
    score: float


def retrieve(query: str, query_lang: str, top_k: int | None = None
             ) -> list[RetrievedChunk]:
    top_k = top_k or config.TOP_K
    client = vector_database.get_client()
    # Nothing saved yet? Return an empty list instead of crashing.
    if not vector_database.collection_exists(client):
        return []
    emb = text_embedder.embed_query(query)

    # Pull results from both searches, then let Qdrant mix them together.
    prefetch = [
        models.Prefetch(
            query=emb.dense,
            using=config.DENSE_VECTOR_NAME,
            limit=config.PREFETCH_K,
        ),
        models.Prefetch(
            query=vector_database.to_sparse_vector(emb.sparse),
            using=config.SPARSE_VECTOR_NAME,
            limit=config.PREFETCH_K,
        ),
    ]

    # Get a few extra so the language bonus can reorder before we cut the list.
    fused_limit = max(top_k, config.PREFETCH_K) if config.SAME_LANG_BOOST else top_k

    resp = client.query_points(
        collection_name=config.QDRANT_COLLECTION,
        prefetch=prefetch,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=fused_limit,
        with_payload=True,
    )

    chunks: list[RetrievedChunk] = []
    for pt in resp.points:
        payload = pt.payload or {}
        score = float(pt.score)
        if config.SAME_LANG_BOOST and payload.get("source_lang") == query_lang:
            score += config.SAME_LANG_BOOST
        chunks.append(RetrievedChunk(
            text=payload.get("text", ""),
            source=payload.get("source", "?"),
            source_lang=payload.get("source_lang", "?"),
            score=score,
        ))

    chunks.sort(key=lambda c: c.score, reverse=True)
    return chunks[:top_k]
