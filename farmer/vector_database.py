"""
Talk to the place where we keep the document vectors.

Normally that is Qdrant. If Qdrant cannot be reached -- no internet, Docker not
running, or a free cloud cluster switched off after a few idle weeks -- we fall
back to the local store in local_store.py instead of killing the app. Both
answer to the same method names, so the rest of the project never finds out
which one it got.

Keeping all of this in one file means we could swap the database by changing
only this file.
"""

from __future__ import annotations

from qdrant_client import QdrantClient, models

import config
from farmer.local_store import LocalStore

_client = None          # the one we settled on
_backend = "none"       # "qdrant" or "local", for the UI to show
_why_local = ""         # what went wrong with Qdrant, if anything


def _try_qdrant():
    """Open Qdrant and actually talk to it. Returns None if it is not there."""
    client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY,
                          timeout=config.QDRANT_TIMEOUT)
    # Constructing the client does not connect to anything, so make one real
    # call. Better to find out here than halfway through ingesting.
    client.get_collections()
    return client


def get_client():
    """
    The client everything else uses. Decided once, then remembered.

    VECTOR_BACKEND in config picks the behaviour:
      "auto"   -> try Qdrant, quietly fall back to local  (the default)
      "qdrant" -> Qdrant only, and let the error through if it is down
      "local"  -> never even try Qdrant
    """
    global _client, _backend, _why_local
    if _client is not None:
        return _client

    choice = config.VECTOR_BACKEND
    if choice == "local":
        _client, _backend, _why_local = LocalStore(), "local", "set in config"
        return _client

    try:
        _client, _backend = _try_qdrant(), "qdrant"
    except Exception as exc:
        if choice == "qdrant":
            raise
        _why_local = _short_reason(exc)
        _client, _backend = LocalStore(), "local"
    return _client


def _short_reason(exc: Exception) -> str:
    """Turn a wall of stack trace into one line a student can act on."""
    text = str(exc)
    if "404" in text:
        return ("the cluster answered 404 — it was probably deleted, or it is "
                "older than Qdrant 1.9")
    if "timed out" in text.lower() or "timeout" in text.lower():
        return "the cluster did not answer in time"
    if "Name or service not known" in text or "getaddrinfo" in text:
        return "that address does not resolve — check QDRANT_URL in .env"
    if "401" in text or "403" in text:
        return "the API key was refused — check QDRANT_API_KEY in .env"
    return text.split("\n")[0][:120]


def backend() -> str:
    """"qdrant" or "local". Call get_client() first."""
    return _backend


def why_local() -> str:
    """Why we ended up local, in one line. Empty if we are on Qdrant."""
    return _why_local


def reset() -> None:
    """Forget the decision so the next call tries Qdrant again."""
    global _client, _backend, _why_local
    _client, _backend, _why_local = None, "none", ""


def collection_exists(client) -> bool:
    """
    Is our collection there yet?

    We deliberately do not call client.collection_exists(). That asks
    /collections/{name}/exists, which only exists in Qdrant 1.9 and up; an
    older server replies 404 and the client raises instead of returning False.
    Listing the collections works on every version ever shipped.
    """
    try:
        names = {c.name for c in client.get_collections().collections}
    except Exception:
        return False
    return config.QDRANT_COLLECTION in names


def count(client) -> int:
    """How many chunks are indexed. -1 means we could not ask."""
    try:
        if not collection_exists(client):
            return 0
        return client.count(config.QDRANT_COLLECTION, exact=True).count
    except Exception:
        return -1


def ensure_collection(client, recreate: bool = False) -> None:
    """Create the collection with named dense + sparse vectors if missing."""
    exists = collection_exists(client)
    if exists and recreate:
        client.delete_collection(config.QDRANT_COLLECTION)
        exists = False
    if exists:
        return

    client.create_collection(
        collection_name=config.QDRANT_COLLECTION,
        vectors_config={
            config.DENSE_VECTOR_NAME: models.VectorParams(
                size=config.EMBED_DIM,
                distance=models.Distance.COSINE,
            )
        },
        sparse_vectors_config={
            config.SPARSE_VECTOR_NAME: models.SparseVectorParams(
                index=models.SparseIndexParams(on_disk=False)
            )
        },
    )
    # Index source_lang so we can filter/inspect by language cheaply.
    client.create_payload_index(
        collection_name=config.QDRANT_COLLECTION,
        field_name="source_lang",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )


def to_sparse_vector(sparse: dict[int, float]) -> models.SparseVector:
    return models.SparseVector(
        indices=list(sparse.keys()),
        values=list(sparse.values()),
    )


def build_point(point_id, dense, sparse, payload) -> models.PointStruct:
    return models.PointStruct(
        id=point_id,
        vector={
            config.DENSE_VECTOR_NAME: dense,
            config.SPARSE_VECTOR_NAME: to_sparse_vector(sparse),
        },
        payload=payload,
    )
