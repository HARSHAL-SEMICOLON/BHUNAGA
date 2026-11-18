#!/usr/bin/env python3
"""
Test how good the system is.

It runs a list of test questions in English, Hindi and Marathi, then gives
simple scores: did it find the right text, did it answer in the right language,
did the answer actually use what was found, and did it invent any numbers.

Three ways of producing the answer can be compared:

    single     one model call
    council    three experts and a chairman          (4 calls)
    selfcons   the same prompt sampled four times    (4 calls)

The third one is the point. Comparing a four-call council against a one-call
baseline cannot tell you whether the expert roles help or whether four calls
simply beat one. "selfcons" spends the same four calls with no structure at
all, so the council only earns its keep if it beats that too.

Resuming
--------
A full three-arm run is several times Groq's free daily token allowance. So
every finished row is written out immediately, and a later run skips whatever
is already in the file. Hit the cap, come back tomorrow, run the same command
again, and it carries on from where it stopped.

    python evaluate.py --no-generate                      # search only, no key
    python evaluate.py --modes single council selfcons    # the full comparison
    python evaluate.py --report                           # just read + report
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import config
from farmer import scoring, searcher, stats

MODES = ("single", "council", "selfcons")

# Groq's free tier is capped on tokens per day. Stopping a little short leaves
# room for the final call to finish rather than being cut off halfway.
DEFAULT_BUDGET = 180_000

# the columns, in the order they appear in the CSV
FIELDS = ["id", "lang", "strategy", "mode", "hit_at_k", "keyword_recall",
          "first_hit_rr", "same_lang_ratio", "source_match", "lang_correct",
          "answer_kw", "grounded", "consensus", "experts", "answer"]


def load_questions(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["items"]


def row_key(row: dict) -> tuple:
    """What makes two rows the same piece of work."""
    return (row["id"], row["lang"], row.get("strategy", "-"),
            row.get("mode", "-"))


def load_done(path: Path) -> dict[tuple, dict]:
    """Rows already finished by an earlier run, so we do not pay for them twice."""
    if not path.exists():
        return {}
    done = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue        # a half-written final line from a killed run
        done[row_key(row)] = row
    return done


def run_one(item: dict, lang: str, do_generate: bool,
            mr_strategy: str | None, mode: str = "-") -> dict:
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
        "mode": mode,
        **scoring.score_to_dict(rscore),
        "lang_correct": "", "answer_kw": "", "grounded": "",
        "consensus": "", "experts": "", "answer": "",
    }

    if do_generate:
        if lang == "mr" and mr_strategy:
            config.MARATHI_STRATEGY = mr_strategy
        from farmer import answer_writer
        ans = answer_writer.generate(question, query_lang=lang, chunks=chunks,
                                     mode=mode)
        row["lang_correct"] = scoring.score_language(ans.text, lang)
        row["answer_kw"] = scoring.score_answer_keywords(ans.text, keywords)
        row["grounded"] = scoring.score_grounding(ans.text, chunks)
        row["answer"] = ans.text.replace("\n", " ")[:280]
        # council.Verdict and self_consistency.Consensus both carry these
        panel = ans.council
        if panel is not None:
            verdict = getattr(panel, "verdict", panel)
            row["consensus"] = getattr(verdict, "score", "")
            row["experts"] = len(getattr(verdict, "spoke", []) or [])

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


def plan(items, langs, modes, mr_strategies, do_generate) -> list[tuple]:
    """Every piece of work this run could do, in a stable order."""
    jobs = []
    for item in items:
        for lang in langs:
            for mode in modes:
                strategies = (mr_strategies if lang == "mr" and do_generate
                              else [None])
                for strategy in strategies:
                    jobs.append((item, lang, strategy, mode))
    return jobs


def write_rows(out: Path, rows: list[dict]) -> None:
    """Rewrite the CSV from every row we have. The JSONL is the append log."""
    with open(f"{out}.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def table(rows: list[dict]) -> None:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["lang"], row["strategy"], row["mode"])].append(row)

    def num(agg, key):
        value = agg.get(key, "-")
        return f"{value:.2f}" if isinstance(value, float) else "  - "

    header = (f"{'lang':4} {'strategy':16} {'mode':9} {'hit@k':6} {'kw_rec':7} "
              f"{'MRR':6} {'same_lg':8} {'lang_ok':8} {'ans_kw':7} {'ground':6}")
    print(header)
    print("-" * len(header))
    for (lang, strategy, mode), group in sorted(groups.items()):
        agg = scoring.aggregate(group)
        print(f"{lang:4} {strategy:16} {mode:9} "
              f"{agg.get('hit_at_k', 0):.2f}   "
              f"{agg.get('keyword_recall', 0):.2f}    "
              f"{agg.get('first_hit_rr', 0):.2f}   "
              f"{agg.get('same_lang_ratio', 0):.2f}     "
              f"{num(agg, 'lang_correct')}     "
              f"{num(agg, 'answer_kw')}   "
              f"{num(agg, 'grounded')}")


METRICS = (("grounded", "numbers traceable"),
           ("answer_kw", "answer keyword recall"),
           ("lang_correct", "answered in language"))


def compare_arms(rows: list[dict]) -> None:
    """The headline. Paired, with an interval, because n is small."""
    by_mode = defaultdict(list)
    for row in rows:
        if row.get("answer"):
            by_mode[row["mode"]].append(row)

    pairs = [(a, b) for a, b in (("single", "council"),
                                 ("single", "selfcons"),
                                 ("selfcons", "council"))
             if by_mode.get(a) and by_mode.get(b)]
    if not pairs:
        return

    print("\n" + "=" * 72)
    print("ARM COMPARISON  (paired by question, 95% bootstrap interval)")
    print("=" * 72)

    for name_a, name_b in pairs:
        print(f"\n{name_a}  vs  {name_b}")
        print("-" * 72)
        print(f"{'metric':24} {name_a:>9} {name_b:>9} {'change':>9} "
              f"{'95% CI':>18}  w/l/t")
        for metric, label in METRICS:
            result = stats.compare(by_mode[name_a], by_mode[name_b], metric)
            if result.n == 0:
                continue
            flag = "*" if result.significant else " "
            print(f"{label:24} {result.mean_a:9.2f} {result.mean_b:9.2f} "
                  f"{result.delta:+9.3f} "
                  f"[{result.low:+.3f},{result.high:+.3f}]{flag} "
                  f"{result.wins_b}/{result.wins_a}/{result.ties}")

    print("\n* = the interval misses zero. Unmarked rows show no reliable")
    print("  difference at this sample size, which is a finding, not a gap.")

    if by_mode.get("council") and by_mode.get("selfcons"):
        print("\nRead 'selfcons vs council' first. Both spend four model calls,")
        print("so it isolates what the expert roles add over plain repetition.")
        print("If single < selfcons but selfcons = council, the gain came from")
        print("sampling, not from the structure.")

    for mode in ("council", "selfcons"):
        scores = [float(r["consensus"]) for r in by_mode.get(mode, [])
                  if str(r.get("consensus", "")).strip() not in ("", "None")]
        if scores:
            print(f"\nmean agreement score, {mode}: "
                  f"{sum(scores) / len(scores):.0f}/100 over {len(scores)} answers")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="eval/questions.json")
    ap.add_argument("--out", default="eval/results")
    ap.add_argument("--langs", nargs="+", default=list(config.SUPPORTED_LANGS),
                    choices=list(config.SUPPORTED_LANGS))
    ap.add_argument("--no-generate", action="store_true",
                    help="retrieval-only; skips Groq so no API key needed")
    ap.add_argument("--mr-strategies", nargs="+", default=["native"],
                    choices=["native", "translate_after"])
    ap.add_argument("--limit", type=int, default=0,
                    help="only the first N questions")
    ap.add_argument("--modes", nargs="+", default=None, choices=list(MODES),
                    help="which answering arms to run. 'selfcons' is the "
                         "equal-compute control for 'council'")
    ap.add_argument("--council", default=None,
                    choices=["config", "on", "off", "both"],
                    help="older two-way switch, kept so old commands still run")
    ap.add_argument("--budget-tokens", type=int, default=DEFAULT_BUDGET,
                    help=f"stop before spending more than this many tokens "
                         f"(default {DEFAULT_BUDGET}, Groq free tier is 200k/day)")
    ap.add_argument("--report", action="store_true",
                    help="do not run anything; read the saved rows and report")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore saved rows and redo everything")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    log = Path(f"{out}.jsonl")

    # --report just reads what previous runs left behind
    if args.report:
        done = load_done(log)
        if not done:
            print(f"Nothing saved at {log}. Run the evaluation first.")
            raise SystemExit(1)
        rows = list(done.values())
        print(f"\n{len(rows)} saved rows from {log}\n")
        table(rows)
        compare_arms(rows)
        return

    # settle which arms to run
    if args.modes:
        modes = list(dict.fromkeys(args.modes))
    elif args.council:
        modes = {"config": ["council" if config.COUNCIL_ENABLED else "single"],
                 "on": ["council"], "off": ["single"],
                 "both": ["single", "council"]}[args.council]
    else:
        modes = ["council" if config.COUNCIL_ENABLED else "single"]

    do_generate = not args.no_generate
    if not do_generate:
        modes = ["-"]        # retrieval is identical in every arm

    preflight()

    items = load_questions(Path(args.questions))
    if args.limit:
        items = items[:args.limit]

    done = {} if args.fresh else load_done(log)
    if args.fresh and log.exists():
        log.unlink()
    jobs = plan(items, args.langs, modes, args.mr_strategies, do_generate)
    todo = [j for j in jobs
            if (j[0]["id"], j[1], j[2] or "-", j[3]) not in done]

    print(f"\n{len(jobs)} rows planned, {len(jobs) - len(todo)} already done, "
          f"{len(todo)} to run")
    if not todo:
        print("Nothing left to do.\n")
        rows = list(done.values())
        write_rows(out, rows)
        table(rows)
        compare_arms(rows)
        return

    from farmer import answer_writer
    answer_writer.reset_tokens()
    stopped = False

    with open(log, "a", encoding="utf-8") as handle:
        for number, (item, lang, strategy, mode) in enumerate(todo, 1):
            spent = answer_writer.tokens_used()["total"]
            if do_generate and spent >= args.budget_tokens:
                print(f"\nToken budget reached ({spent:,} used). Stopping here "
                      f"so nothing is cut off mid-answer.")
                stopped = True
                break
            try:
                row = run_one(item, lang, do_generate, strategy, mode)
            except Exception as exc:
                message = str(exc)
                print(f"  [{number}/{len(todo)}] {item['id']} {lang} {mode}: "
                      f"FAILED — {message[:120]}")
                # a daily cap is not a bug to retry, it is tomorrow's problem
                if "daily" in message.lower() or "quota" in message.lower():
                    print("\nThat looks like the daily allowance. Everything "
                          "finished so far is saved.")
                    stopped = True
                    break
                continue

            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()      # survive a kill -9 with the row intact
            done[row_key(row)] = row
            if do_generate:
                used = answer_writer.tokens_used()["total"]
                print(f"  [{number}/{len(todo)}] {item['id']:26} {lang} "
                      f"{mode:9} {used:>7,} tok")

    rows = list(done.values())
    write_rows(out, rows)

    print(f"\nEval over {len(items)} questions  |  generate={do_generate}\n")
    table(rows)
    compare_arms(rows)

    if do_generate:
        usage = answer_writer.tokens_used()
        print(f"\nthis run: {usage['calls']} calls, {usage['total']:,} tokens")
    if stopped:
        remaining = len([j for j in jobs
                         if (j[0]["id"], j[1], j[2] or "-", j[3]) not in done])
        print(f"\n{remaining} rows still to do. Run the same command again "
              f"tomorrow and it will carry on.")

    print(f"\nWrote {out}.jsonl and {out}.csv")


if __name__ == "__main__":
    main()
