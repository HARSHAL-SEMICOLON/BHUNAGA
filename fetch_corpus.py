#!/usr/bin/env python3
"""
Download the real agricultural recommendation books into data/sources/.

Why this exists
---------------
The corpus shipped with this project is 24 short notes, about 9,400 words in
all -- a whole crop covered in a paragraph. Retrieval was never the limit; there
was simply almost nothing to retrieve. A Marathi question about chilli thrips
found the best of 114 chunks, and if none of them were about chilli, the council
wrote a confident answer from whatever was nearest.

Why PDFs rather than written summaries
--------------------------------------
It is tempting to have a model read these documents and write tidy notes into
data/. Do not. The entire claim this project makes is that its answers come from
real agricultural documents, and a summary written by a language model is not
one -- it is the model's recollection of one, with the errors that implies.
Worse, the summariser's own warning on the first file tried was "garbled PDF
extraction with some conflicting values", and a conflicting fertiliser dose
written into a knowledge base is a farmer buying the wrong input.

So the PDFs go in whole and ingest.py chunks the actual text. The chunk a farmer
is shown is the university's own words, and the citation is the book's filename.

What these are
--------------
Maharashtra's two state agricultural universities publish an annual book of
research recommendations: the crop, the variety, the dose, the spacing, the
spray and the stage, for the state's own soils and seasons. They are public,
free, and the most authoritative agronomy available for this region.

    MPKV  -- Mahatma Phule Krishi Vidyapeeth, Rahuri (Western Maharashtra)
    PDKV  -- Dr. Panjabrao Deshmukh Krishi Vidyapeeth, Akola (Vidarbha)

Usage
-----
    python fetch_corpus.py              # download everything missing
    python fetch_corpus.py --list       # show the manifest, download nothing
    python fetch_corpus.py --force      # re-download even if present
    python ingest.py                    # then index what arrived
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import requests

import config

DEST = config.DATA_DIR / "sources"
TIMEOUT = 60          # these are large books on university servers
MIN_BYTES = 50_000    # anything smaller is an error page wearing a .pdf name


# `checked` records whether the URL was confirmed to resolve and to contain
# what the description claims, rather than only appearing in a search result.
SOURCES: list[dict] = [
    {
        "file": "MPKV-Recommendations-2025.pdf",
        "url": "https://mpkv.ac.in/Uploads/Research/2025-English_20250808061909.pdf",
        "what": "MPKV Rahuri, 58 research recommendations released in 2025. "
                "Paddy, Bt cotton, pigeonpea, okra, mango, guava, onion, wheat, "
                "maize, soybean, turmeric, sugarcane, brinjal, sorghum, finger "
                "millet, chickpea, pearl millet, sesame, sunflower, horse gram.",
        "checked": True,
    },
    {
        "file": "PDKV-Recommendations-2024.pdf",
        "url": "https://www.pdkv.ac.in/Circulars/Recom-2024English.pdf",
        "what": "PDKV Akola, 72 recommendations from 2023-24, roughly 40-50 "
                "crop-specific. Adds Nagpur mandarin, pomegranate, grape, "
                "banana, chilli, garlic, safflower, linseed, groundnut.",
        "checked": True,
    },
    {
        "file": "MPKV-Wheat.pdf",
        "url": "https://mpkv.ac.in/Uploads/Research/4. Wheat_20200110053545.pdf",
        "what": "MPKV wheat package: varieties, 1-15 Nov sowing window, paired "
                "row 15/30 cm, 120:60:40 NPK timely and 90:60:40 late, drip "
                "fertigation schedule, irrigation at 41 and 62 DAS.",
        "checked": True,
    },
    {
        "file": "MPKV-Paddy.pdf",
        "url": "https://mpkv.ac.in/Uploads/Research/1. Paddy_20200110043402.pdf",
        "what": "MPKV paddy package of practices.",
        "checked": False,
    },
    # The yearly PDKV books follow one URL pattern. Each adds a different set
    # of recommendations, so several years is more coverage, not duplication.
    *[
        {
            "file": f"PDKV-Recommendations-{year}.pdf",
            "url": f"https://www.pdkv.ac.in/Circulars/Recom-{year}English.pdf",
            "what": f"PDKV Akola annual research recommendations, {year}.",
            "checked": False,
        }
        for year in (2022, 2021, 2020, 2019, 2018)
    ],
]


def fetch(source: dict, force: bool = False) -> tuple[str, str]:
    """Download one source. Returns (status, detail). Never raises."""
    target = DEST / source["file"]

    if target.exists() and not force:
        return "skip", f"already here ({target.stat().st_size // 1024} KB)"

    try:
        response = requests.get(source["url"], timeout=TIMEOUT,
                                headers={"User-Agent": "Bhunaga/1.0 (student project)"})
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        return "fail", f"{type(exc).__name__}: {str(exc)[:90]}"

    body = response.content
    if len(body) < MIN_BYTES:
        return "fail", f"only {len(body)} bytes — probably an error page"
    if not body.startswith(b"%PDF"):
        return "fail", "the server did not return a PDF"

    target.write_bytes(body)
    return "ok", f"{len(body) // 1024} KB"


def write_provenance(results: list[tuple[dict, str, str]]) -> None:
    """
    Record where every file came from, next to the files.

    A knowledge base whose origin is undocumented is a liability: six months
    from now nobody can tell which advice came from which university, or how
    old it is.
    """
    today = dt.date.today().isoformat()
    lines = [
        "# Where these documents came from",
        "",
        f"Downloaded by `fetch_corpus.py` on {today}.",
        "",
        "These are public research recommendations from Maharashtra's state",
        "agricultural universities. They are ingested whole, so a chunk shown",
        "to a farmer is the university's own text, not a summary of it.",
        "",
    ]
    for source, status, detail in results:
        mark = {"ok": "+", "skip": "=", "fail": "!"}.get(status, "?")
        lines += [f"## {mark} {source['file']}", "",
                  f"- Source: <{source['url']}>",
                  f"- Status: {status} ({detail})",
                  f"- Contents: {source['what']}", ""]
    (DEST / "SOURCES.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true",
                        help="show the manifest and exit")
    parser.add_argument("--force", action="store_true",
                        help="download again even if the file is present")
    args = parser.parse_args()

    if args.list:
        for source in SOURCES:
            seen = "verified" if source["checked"] else "unverified"
            print(f"  {source['file']:38} [{seen}]\n      {source['url']}")
        return 0

    DEST.mkdir(parents=True, exist_ok=True)
    print(f"Downloading into {DEST}\n")

    results = []
    for source in SOURCES:
        status, detail = fetch(source, force=args.force)
        mark = {"ok": "OK  ", "skip": "--  ", "fail": "FAIL"}[status]
        print(f"  {mark} {source['file']:38} {detail}")
        results.append((source, status, detail))

    write_provenance(results)

    got = sum(1 for _, s, _ in results if s in ("ok", "skip"))
    failed = [s["file"] for s, st, _ in results if st == "fail"]
    print(f"\n{got} of {len(SOURCES)} available in {DEST}")
    if failed:
        print("Could not fetch: " + ", ".join(failed))
        print("These are university servers and they do go down. Re-run later, "
              "or download by hand from the URL in SOURCES.md.")
    if got:
        print("\nNext:  python ingest.py        (this will take a while)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
