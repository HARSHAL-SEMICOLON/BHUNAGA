"""
Turn text into numbers (vectors) with the BGE-M3 model.

One model understands all three languages, so a Marathi question can match an
English document. For each text it makes two things:
  - dense vector  -> the meaning of the text
  - sparse vector -> the important exact words
Having both lets us do a stronger "hybrid" search.

There are two ways to run the same model, chosen by config.EMBED_BACKEND:

  "flagembedding"  BGE-M3 through torch. About 3 GB of RAM. The default, and
                   what models/local_kb was built with.
  "onnx"           The same model exported to ONNX and quantised to int8.
                   Under 1 GB and needs no torch, which is what makes a free
                   host possible. Quantising moves the vectors very slightly,
                   so an index built with one backend must be searched with
                   the same backend -- see scripts/build_onnx_embedder.py.

Both return the identical Embedding shape, so nothing downstream changes.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import config

_model = None          # FlagEmbedding model
_ort = None            # (onnxruntime session, tokenizer)


@dataclass
class Embedding:
    dense: list[float]
    sparse: dict[int, float]


def backend() -> str:
    """Which implementation is active. The UI shows this on the status line."""
    return "onnx" if config.EMBED_BACKEND == "onnx" else "flagembedding"


def is_loaded() -> bool:
    """
    Is the embedding model already in memory?

    The UI asks before it picks a spinner message. The model is large and is
    fetched on first use, so on a freshly woken deployment the first question
    sits for a while behind whatever message is on screen. "Finding the
    answer..." for two minutes reads as a hang and people close the tab; saying
    it is a one-time setup reads as a wait.
    """
    return _model is not None if backend() == "flagembedding" else _ort is not None


# ── FlagEmbedding (torch) ───────────────────────────────────────────────────
def _load_flag():
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


def _embed_flag(texts: list[str]) -> list[Embedding]:
    model = _load_flag()
    out = model.encode(
        texts,
        batch_size=config.EMBED_BATCH_SIZE,
        max_length=config.EMBED_MAX_LENGTH,
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False,
    )
    dense, sparse = out["dense_vecs"], out["lexical_weights"]
    return [Embedding(dense=[float(x) for x in dense[i]],
                      sparse=_to_sparse_dict(sparse[i]))
            for i in range(len(texts))]


# ── ONNX int8 (no torch) ────────────────────────────────────────────────────
def _load_onnx():
    """Open the quantised model. Downloads it once, then reads the HF cache."""
    global _ort
    if _ort is not None:
        return _ort

    import onnxruntime as ort
    from transformers import AutoTokenizer

    path = config.ONNX_LOCAL_PATH
    if not path:
        if not config.ONNX_REPO_ID:
            raise RuntimeError(
                "EMBED_BACKEND=onnx needs ONNX_REPO_ID (your Hugging Face model "
                "repo) or ONNX_LOCAL_PATH. See scripts/build_onnx_embedder.py.")
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(repo_id=config.ONNX_REPO_ID,
                               filename=config.ONNX_FILENAME)

    opts = ort.SessionOptions()
    # One thread per core is the wrong default on a shared free host: the extra
    # threads contend rather than help, and each one costs memory.
    opts.intra_op_num_threads = config.ONNX_THREADS
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    session = ort.InferenceSession(path, opts, providers=["CPUExecutionProvider"])
    tokenizer = AutoTokenizer.from_pretrained(config.EMBED_MODEL_NAME)
    _ort = (session, tokenizer)
    return _ort


def _process_token_weights(token_weights, input_ids, tokenizer) -> dict[int, float]:
    """
    Collapse per-token weights into {token_id: weight}.

    This mirrors FlagEmbedding's own routine exactly -- same skipped special
    tokens, same max-not-sum when a token repeats. It has to: the weights in
    models/local_kb/meta.json were produced by that routine, and the sparse
    score is a dot product over shared token ids. A different rule here would
    silently halve recall rather than raise anything.
    """
    unused = {tokenizer.cls_token_id, tokenizer.eos_token_id,
              tokenizer.pad_token_id, tokenizer.unk_token_id}
    result: dict[int, float] = defaultdict(float)
    for w, idx in zip(token_weights, input_ids):
        w = float(w)
        if idx not in unused and w > 0 and w > result[idx]:
            result[int(idx)] = w
    return dict(result)


def _embed_onnx(texts: list[str]) -> list[Embedding]:
    import numpy as np
    session, tokenizer = _load_onnx()

    results: list[Embedding] = []
    batch = max(1, config.EMBED_BATCH_SIZE)
    for start in range(0, len(texts), batch):
        part = texts[start:start + batch]
        enc = tokenizer(part, padding="longest", truncation=True,
                        max_length=config.EMBED_MAX_LENGTH, return_tensors="np")
        feed = {i.name: enc[i.name] for i in session.get_inputs() if i.name in enc}
        out = session.run(None, feed)

        dense = np.asarray(out[0])
        token_weights = np.asarray(out[1]).squeeze(-1)
        ids = enc["input_ids"].tolist()
        for row in range(len(part)):
            results.append(Embedding(
                dense=[float(x) for x in dense[row]],
                sparse=_process_token_weights(token_weights[row], ids[row], tokenizer),
            ))
    return results


# ── public API ──────────────────────────────────────────────────────────────
def embed_texts(texts: list[str]) -> list[Embedding]:
    """Embed a batch. Returns dense + sparse for each text."""
    if not texts:
        return []
    return _embed_onnx(texts) if backend() == "onnx" else _embed_flag(texts)


def embed_query(text: str) -> Embedding:
    """Convenience single-text wrapper for the query path."""
    return embed_texts([text])[0]
