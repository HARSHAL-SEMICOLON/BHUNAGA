"""
Turn text into numbers (vectors) with the BGE-M3 model.

One model understands all three languages, so a Marathi question can match an
English document. For each text it makes two things:
  - dense vector  -> the meaning of the text
  - sparse vector -> the important exact words
Having both lets us do a stronger "hybrid" search.
"""

from __future__ import annotations

from dataclasses import dataclass

import config

_model = None


@dataclass
class Embedding:
    dense: list[float]
    sparse: dict[int, float]


def _load():
    global _model
    if _model is not None:
        return _model
    from FlagEmbedding import BGEM3FlagModel
    _model = BGEM3FlagModel(config.EMBED_MODEL_NAME,
                            use_fp16=config.EMBED_USE_FP16)
    return _model


def _to_sparse_dict(lexical_weights) -> dict[int, float]:
    # FlagEmbedding returns {token_id_str: weight}; normalise keys to int.
    return {int(k): float(v) for k, v in lexical_weights.items()}


def embed_texts(texts: list[str]) -> list[Embedding]:
    """Embed a batch. Returns dense + sparse for each text."""
    if not texts:
        return []
    model = _load()
    out = model.encode(
        texts,
        batch_size=config.EMBED_BATCH_SIZE,
        max_length=config.EMBED_MAX_LENGTH,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )
    dense = out["dense_vecs"]
    sparse = out["lexical_weights"]
    results: list[Embedding] = []
    for i in range(len(texts)):
        results.append(Embedding(
            dense=[float(x) for x in dense[i]],
            sparse=_to_sparse_dict(sparse[i]),
        ))
    return results


def embed_query(text: str) -> Embedding:
    """Convenience single-text wrapper for the query path."""
    return embed_texts([text])[0]
