#!/usr/bin/env python3
"""
Add documents to the search system.

Steps: read each file, cut it into small pieces, find each piece's language,
turn the pieces into number-vectors with BGE-M3, and save them in Qdrant.

Run it like:
    python ingest.py                 # add everything in the data folder
    python ingest.py --recreate      # clear and build again
"""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path

from tqdm import tqdm

import config
from farmer import text_embedder, language_detector, vector_database


# Loading
def load_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if suffix == ".docx":
        import docx
        return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""  # unsupported -> skipped


def iter_source_files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".pdf", ".docx", ".txt", ".md"):
            yield p


# Chunking (character-based with overlap; cheap and language-agnostic)
def chunk_text(text: str) -> list[str]:
    text = " ".join(text.split())  # collapse whitespace
    if not text:
        return []
    size, overlap = config.CHUNK_SIZE, config.CHUNK_OVERLAP
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


# Main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=str(config.DATA_DIR),
                    help="file or directory to ingest")
    ap.add_argument("--recreate", action="store_true",
                    help="drop and rebuild the Qdrant collection")
    args = ap.parse_args()

    root = Path(args.path)
    files = [root] if root.is_file() else list(iter_source_files(root))
    if not files:
        print(f"No supported documents found under {root}. "
              f"Drop PDFs/DOCX/TXT/MD into ./data and re-run.")
        return

    client = vector_database.get_client()
    vector_database.ensure_collection(client, recreate=args.recreate)

    total_chunks = 0
    for path in files:
        text = load_text(path)
        chunks = chunk_text(text)
        if not chunks:
            print(f"  (skip, no text) {path.name}")
            continue

        embs = text_embedder.embed_texts(chunks)

        points = []
        for chunk, emb in zip(chunks, embs):
            lang = language_detector.detect(chunk).lang
            payload = {
                "text": chunk,
                "source": path.name,
                "source_lang": lang,
            }
            points.append(vector_database.build_point(
                point_id=str(uuid.uuid4()),
                dense=emb.dense,
                sparse=emb.sparse,
                payload=payload,
            ))

        client.upsert(collection_name=config.QDRANT_COLLECTION, points=points)
        total_chunks += len(points)
        print(f"  + {len(points):4d} chunks  {path.name}")

    print(f"\nDone. Upserted {total_chunks} chunks into "
          f"'{config.QDRANT_COLLECTION}'.")


if __name__ == "__main__":
    main()
