#!/usr/bin/env python3
"""
Ask a question from the command line.

It finds the language of your question, searches the documents, and prints
the answer in the same language.

Run it like:
    python query.py "How much urea per acre for wheat?"
    python query.py --interactive
"""

from __future__ import annotations

import argparse
import sys

import config
from farmer import answer_writer, language_detector, searcher


def _print_panel(panel) -> None:
    """Show what each expert said and how the chairman scored them."""
    v = panel.verdict
    print(f"\n[council] agreement {v.score}/100 ({v.label}) — "
          f"chairman said {v.chairman_score}, word overlap "
          f"{v.word_overlap:.2f}")
    for op in panel.opinions:
        head = f"  {op.seat.icon} {op.seat.title}"
        if op.failed:
            print(f"{head}: (failed — {op.error})")
        elif op.abstained:
            print(f"{head}: (nothing in the documents for this seat)")
        else:
            print(f"{head}:")
            for line in op.text.splitlines():
                if line.strip():
                    print(f"      {line.strip()}")
    for c in v.conflicts:
        print(f"  ⚠ they disagreed on: {c}")


def answer_query(text: str, show_context: bool = False,
                 use_council: bool | None = None,
                 show_panel: bool = False) -> None:
    lang = language_detector.detect(text)
    print(f"\n[lang] {config.LANG_NAMES.get(lang.lang, lang.lang)} "
          f"({lang.lang}, conf={lang.confidence:.2f})")

    chunks = searcher.retrieve(text, query_lang=lang.lang)
    if not chunks:
        print("[retrieve] no chunks — has the collection been ingested?")
        return

    if show_context:
        print("\n[context]")
        for i, c in enumerate(chunks, 1):
            preview = c.text[:160].replace("\n", " ")
            print(f"  [{i}] {c.score:.3f} {c.source_lang} {c.source}: {preview}...")

    ans = answer_writer.generate(text, query_lang=lang.lang, chunks=chunks,
                                 use_council=use_council)
    if show_panel and ans.council is not None:
        _print_panel(ans.council)

    print(f"\n[answer | strategy={ans.strategy}]\n{ans.text}\n")
    if ans.council is not None and not show_panel:
        v = ans.council.verdict
        print(f"[consensus] {v.score}/100 ({v.label}), "
              f"{len(v.spoke)} of 3 experts spoke\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="*", help="the question to ask")
    ap.add_argument("--show-context", action="store_true",
                    help="print retrieved chunks before the answer")
    ap.add_argument("--interactive", action="store_true",
                    help="REPL loop")
    ap.add_argument("--council", dest="council", action="store_true",
                    default=None,
                    help="use the three-expert council (default from config)")
    ap.add_argument("--no-council", dest="council", action="store_false",
                    help="plain single-model answer, for comparison")
    ap.add_argument("--show-panel", action="store_true",
                    help="print each expert's opinion before the final answer")
    args = ap.parse_args()

    # asking to see the panel obviously means you want the panel to run
    council = True if args.show_panel and args.council is None else args.council

    if args.interactive:
        print("Trilingual RAG (en/hi/mr). Ctrl-C to exit.")
        try:
            while True:
                q = input("\n> ").strip()
                if q:
                    answer_query(q, show_context=args.show_context,
                                 use_council=council, show_panel=args.show_panel)
        except (KeyboardInterrupt, EOFError):
            print("\nbye.")
        return

    if not args.question:
        ap.error("provide a question or use --interactive")
    answer_query(" ".join(args.question), show_context=args.show_context,
                 use_council=council, show_panel=args.show_panel)


if __name__ == "__main__":
    sys.exit(main())
