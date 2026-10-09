#!/usr/bin/env python3
"""
Test how good the system is.

It runs a list of test questions in English, Hindi and Marathi, then gives
simple scores: did it find the right text, did it answer in the right language,
did the answer actually use what was found, and did it invent any numbers.

It can also A/B two things:

  * the Marathi strategy — answer natively, or reason in English and translate
  * the council — one model answering alone, versus three experts and a chairman

The council comparison is the one to put in the report. Without a number, "we
added multi-agent consensus" is a claim; with one it is a result.

Run it like:
    python evaluate.py --no-generate            # search only, no API key needed
    python evaluate.py --council both           # single agent vs council
    python evaluate.py --council both --langs mr
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import config
from farmer import scoring, searcher


def load_questions(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["items"]


def run_one(item: dict, lang: str, do_generate: bool,
            mr_strategy: str | None, use_council: bool | None = None) -> dict:
    """Score one question in one language under one setting."""
    question = item["questions"][lang]
    keywords = item.get("answer_keywords", [])
    expected_source = item.get("expected_source", "")

    chunks = searcher.retrieve(question, query_lang=lang)
    rscore = scoring.score_retrieval(chunks, keywords, lang, expected_source)

    row = {
        "id": item["id"],
        "lang": lang,
        "strategy": mr_strategy or "-",
        "mode": {True: "council", False: "single"}.get(use_council, "-"),
        **scoring.score_to_dict(rscore),
        "lang_correct": "",
        "answer_kw": "",
        "grounded": "",
        "consensus": "",
        "experts": "",
        "answer": "",
    }

    if do_generate:
        # Apply the requested Marathi strategy for this run.
        if lang == "mr" and mr_strategy:
            config.MARATHI_STRATEGY = mr_strategy
        from farmer import answer_writer
        ans = answer_writer.generate(question, query_lang=lang, chunks=chunks,
                                     use_council=use_council)
        row["lang_correct"] = scoring.score_language(ans.text, lang)
        row["answer_kw"] = scoring.score_answer_keywords(ans.text, keywords)
        row["grounded"] = scoring.score_grounding(ans.text, chunks)
        row["answer"] = ans.text.replace("\n", " ")[:280]
        if ans.council is not None:
            row["consensus"] = ans.council.verdict.score
            row["experts"] = len(ans.council.verdict.spoke)

    return row


def preflight() -> None:
    """Refuse to score anything against an index that is not there.

    An empty index does not crash. searcher.retrieve returns an empty list,
    every metric comes out 0.00, and the results table looks exactly like a
    model that cannot retrieve -- which sends you debugging the embeddings
    instead of running ingest.py. The two failures are indistinguishable from
    the scores alone, so check which one it is before scoring anything.
    """
    from farmer import vector_database

    vector_database.reset()
    client = vector_database.get_client()
    where = vector_database.backend()
    count = vector_database.count(client)

    if count > 0:
        print(f"index: {count} chunks  |  backend: {where}")
        return

    print(f"\nThe knowledge base is empty -- 0 chunks on the {where} backend.")
    if where != "qdrant":
        print(f"Qdrant was not used: {vector_database.why_local()}")
    print("\nEvery metric below would be 0.00, which reads as a retrieval")
    print("failure rather than a missing index. Build the index first:\n")
    print("    python ingest.py --recreate\n")
    raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="eval/questions.json")
    ap.add_argument("--out", default="eval/results")
    ap.add_argument("--langs", nargs="+", default=list(config.SUPPORTED_LANGS),
                    choices=list(config.SUPPORTED_LANGS))
    ap.add_argument("--no-generate", action="store_true",
                    help="retrieval-only; skips Groq so no API key needed")
    ap.add_argument("--mr-strategies", nargs="+", default=["native"],
                    choices=["native", "translate_after"],
                    help="Marathi strategies to A/B compare")
    ap.add_argument("--limit", type=int, default=0,
                    help="only the first N questions. A full --council both "
                         "run is ~600k tokens and will not fit in Groq's free "
                         "200k/day; --limit 4 --langs mr does fit")
    ap.add_argument("--council", default="config",
                    choices=["config", "on", "off", "both"],
                    help="'both' runs each question twice, once with a single "
                         "model and once with the council, and reports the gap")
    args = ap.parse_args()

    preflight()

    items = load_questions(Path(args.questions))
    if args.limit:
        items = items[:args.limit]
    do_generate = not args.no_generate

    # which council settings to run. None means "whatever config says".
    modes: list[bool | None] = {
        "config": [None], "on": [True], "off": [False], "both": [False, True],
    }[args.council]
    if not do_generate:
        modes = [None]      # retrieval is identical either way, so do not double

    rows: list[dict] = []
    for item in items:
        for lang in args.langs:
            for mode in modes:
                if lang == "mr" and do_generate:
                    for strat in args.mr_strategies:
                        rows.append(run_one(item, lang, do_generate, strat, mode))
                else:
                    rows.append(run_one(item, lang, do_generate, None, mode))

    # --- write per-question outputs ---
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(f"{out}.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(f"{out}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # --- aggregate by (lang, strategy, mode) ---
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["lang"], r["strategy"], r["mode"])].append(r)

    def num(agg, key):
        value = agg.get(key, "-")
        return f"{value:.2f}" if isinstance(value, float) else "  - "

    print(f"\nEval over {len(items)} questions  |  generate={do_generate}\n")
    header = (f"{'lang':4} {'strategy':16} {'mode':8} {'hit@k':6} {'kw_rec':7} "
              f"{'MRR':6} {'same_lg':8} {'lang_ok':8} {'ans_kw':7} {'ground':6}")
    print(header)
    print("-" * len(header))
    for (lang, strat, mode), grp in sorted(groups.items()):
        agg = scoring.aggregate(grp)
        print(f"{lang:4} {strat:16} {mode:8} "
              f"{agg.get('hit_at_k', 0):.2f}   "
              f"{agg.get('keyword_recall', 0):.2f}    "
              f"{agg.get('first_hit_rr', 0):.2f}   "
              f"{agg.get('same_lang_ratio', 0):.2f}     "
              f"{num(agg, 'lang_correct')}     "
              f"{num(agg, 'answer_kw')}   "
              f"{num(agg, 'grounded')}")

    # --- the headline comparison, when both modes were run ---
    if args.council == "both" and do_generate:
        single = [r for r in rows if r["mode"] == "single"]
        council = [r for r in rows if r["mode"] == "council"]
        if single and council:
            a, b = scoring.aggregate(single), scoring.aggregate(council)
            print("\nSingle model vs council")
            print("-" * 52)
            print(f"{'metric':22} {'single':>8} {'council':>9} {'change':>9}")
            for key, label in (("answer_kw", "answer keyword recall"),
                               ("grounded", "numbers traceable"),
                               ("lang_correct", "answered in language")):
                before, after = a.get(key), b.get(key)
                if isinstance(before, float) and isinstance(after, float):
                    delta = after - before
                    print(f"{label:22} {before:8.2f} {after:9.2f} "
                          f"{delta:+9.2f}")
            scores = [r["consensus"] for r in council
                      if isinstance(r["consensus"], (int, float))]
            if scores:
                print(f"\nmean consensus score: {sum(scores)/len(scores):.0f}/100 "
                      f"over {len(scores)} answers")
            print("\n'numbers traceable' is the one to watch: it is the share of "
                  "figures in the\nanswer that actually appear in the retrieved "
                  "documents. A wrong dose is\nexactly the kind of mistake a "
                  "second opinion is supposed to catch.")

    print(f"\nWrote {out}.jsonl and {out}.csv")


if __name__ == "__main__":
    main()
