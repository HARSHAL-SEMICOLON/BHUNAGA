"""
A small search index that lives on this computer.

Qdrant is the proper home for the vectors, but a free cloud cluster is switched
off after a few idle weeks and then the whole app is dead on the morning of a
demo. So we keep a plain local copy as a backup: numpy for the meaning vectors,
a dictionary for the exact-word vectors, and two files on disk.

It answers to the same method names as the Qdrant client, so nothing else in the
project has to know which one it is talking to.

It is honest about what it is. There is no index -- every search compares the
question against every saved chunk. On a few thousand chunks that is a couple of
milliseconds and nobody notices. On a million it would be far too slow, and at
that point you want the real Qdrant back.

Saved in models/local_kb/:
    dense.npy   the meaning vectors, one row per chunk
    meta.json   the text, where it came from, and the exact-word weights
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

import config

# used by the fusion step below. 60 is the number from the original paper and
# also what Qdrant uses, so our two backends rank things the same way.
RRF_K = 60


@dataclass
class Hit:
    """Shaped like a Qdrant point so searcher.py cannot tell the difference."""
    payload: dict
    score: float
    id: str = ""


@dataclass
class QueryResponse:
    points: list[Hit]


@dataclass
class CountResponse:
    count: int


@dataclass
class _Collection:
    name: str


@dataclass
class CollectionsResponse:
    collections: list[_Collection] = field(default_factory=list)


class LocalStore:
    """Stand-in for QdrantClient, backed by two files."""

    def __init__(self, folder: Path | None = None):
        self.folder = Path(folder or (config.MODELS_DIR / "local_kb"))
        self.dense: np.ndarray | None = None    # (n_chunks, embed_dim)
        self.meta: list[dict] = []              # one entry per row above
        self._made = False                      # has the collection been created
        self._load()

    # saving and loading
    @property
    def _dense_file(self) -> Path:
        return self.folder / "dense.npy"

    @property
    def _meta_file(self) -> Path:
        return self.folder / "meta.json"

    def _load(self) -> None:
        if not (self._dense_file.exists() and self._meta_file.exists()):
            return
        try:
            self.dense = np.load(self._dense_file)
            self.meta = json.loads(self._meta_file.read_text(encoding="utf-8"))
            # sparse keys come back from json as strings, put them back to int
            for m in self.meta:
                m["sparse"] = {int(k): float(v) for k, v in m["sparse"].items()}
            self._made = True
        except Exception:
            # a half-written file from a crashed run. start clean rather than
            # limp along with a broken index.
            self.dense, self.meta, self._made = None, [], False

    def _save(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        if self.dense is not None:
            np.save(self._dense_file, self.dense)
        self._meta_file.write_text(
            json.dumps(self.meta, ensure_ascii=False), encoding="utf-8")

    # the bits of the Qdrant client we actually use
    def get_collections(self) -> CollectionsResponse:
        if self._made:
            return CollectionsResponse([_Collection(config.QDRANT_COLLECTION)])
        return CollectionsResponse([])

    def collection_exists(self, collection_name: str) -> bool:
        return self._made and collection_name == config.QDRANT_COLLECTION

    def create_collection(self, collection_name: str, **kwargs) -> None:
        self._made = True
        self._save()

    def delete_collection(self, collection_name: str) -> None:
        self.dense, self.meta, self._made = None, [], False
        for f in (self._dense_file, self._meta_file):
            f.unlink(missing_ok=True)

    def create_payload_index(self, **kwargs) -> None:
        """Qdrant needs this to filter quickly. We scan everything anyway."""

    def count(self, collection_name: str, exact: bool = True) -> CountResponse:
        return CountResponse(len(self.meta))

    def upsert(self, collection_name: str, points: list) -> None:
        """Add chunks. `points` are the same PointStruct objects Qdrant takes."""
        rows, new_meta = [], []
        for pt in points:
            vectors = pt.vector
            dense = np.asarray(vectors[config.DENSE_VECTOR_NAME], dtype=np.float32)
            sparse_vec = vectors[config.SPARSE_VECTOR_NAME]
            rows.append(dense)
            new_meta.append({
                "id": str(pt.id),
                "sparse": {int(i): float(v) for i, v
                           in zip(sparse_vec.indices, sparse_vec.values)},
                **(pt.payload or {}),
            })
        if not rows:
            return

        block = np.vstack(rows)
        self.dense = block if self.dense is None else np.vstack([self.dense, block])
        self.meta.extend(new_meta)
        self._made = True
        self._save()

    # searching
    def _dense_ranking(self, query: list[float], limit: int) -> list[int]:
        """Cosine similarity. Both sides are normalised so it is just a dot."""
        if self.dense is None or not len(self.dense):
            return []
        q = np.asarray(query, dtype=np.float32)
        q /= (np.linalg.norm(q) or 1.0)
        mat = self.dense
        norms = np.linalg.norm(mat, axis=1)
        norms[norms == 0] = 1.0
        scores = (mat @ q) / norms
        return list(np.argsort(-scores)[:limit])

    def _sparse_ranking(self, indices, values, limit: int) -> list[int]:
        """Dot product on the words the two texts share."""
        query = {int(i): float(v) for i, v in zip(indices, values)}
        if not query:
            return []
        scored = []
        for row, m in enumerate(self.meta):
            weights = m["sparse"]
            # walk the shorter of the two, it is usually the question
            small, big = (query, weights) if len(query) < len(weights) else (weights, query)
            total = sum(w * big[tok] for tok, w in small.items() if tok in big)
            if total > 0:
                scored.append((total, row))
        scored.sort(reverse=True)
        return [row for _, row in scored[:limit]]

    def query_points(self, collection_name: str, prefetch, query=None,
                     limit: int = 8, with_payload: bool = True
                     ) -> QueryResponse:
        """
        Run both searches and fuse them, the way Qdrant's RRF does.

        Reciprocal Rank Fusion only looks at *where* a chunk came in each list,
        never at the raw score. That is the point: a cosine similarity and a
        word-overlap score are on completely different scales and adding them
        together would be meaningless.
        """
        if self.dense is None or not self.meta:
            return QueryResponse([])

        prefetch = list(prefetch or [])
        rankings = []
        for pf in prefetch:
            if pf.using == config.DENSE_VECTOR_NAME:
                rankings.append(self._dense_ranking(pf.query, config.PREFETCH_K))
            elif pf.using == config.SPARSE_VECTOR_NAME:
                rankings.append(self._sparse_ranking(
                    pf.query.indices, pf.query.values, config.PREFETCH_K))

        fused: dict[int, float] = {}
        for ranking in rankings:
            for rank, row in enumerate(ranking):
                fused[row] = fused.get(row, 0.0) + 1.0 / (RRF_K + rank + 1)

        best = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return QueryResponse([
            Hit(payload=self.meta[row], score=score, id=self.meta[row].get("id", ""))
            for row, score in best
        ])
