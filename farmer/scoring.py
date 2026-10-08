"""
Simple ways to give scores, used by the tests and the evaluator.

It checks things like: did the search find a keyword, how high was the first
good result, and is the answer in the right language. It uses no extra libraries
so it is fast and easy to read.
"""

from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass


def _norm(s: str) -> str:  # make text lower-case and tidy for comparing
    s = unicodedata.normalize("NFKC", s or "").casefold()
    return " ".join(s.split())


def _contains(haystack: str, needle: str) -> bool:
    return _norm(needle) in _norm(haystack)


@dataclass
class RetrievalScore:
    hit_at_k: int          # 0/1
    keyword_recall: float
    first_hit_rr: float
    same_lang_ratio: float
    source_match: int      # 0/1, only meaningful if expected_source given


def score_retrieval(chunks, keywords: list[str], query_lang: str,
                    expected_source: str = "") -> RetrievalScore:
    texts = [c.text for c in chunks]
    langs = [c.source_lang for c in chunks]

    found = {kw for kw in keywords if any(_contains(t, kw) for t in texts)}
    keyword_recall = len(found) / len(keywords) if keywords else 0.0

    first_rr = 0.0
    for rank, t in enumerate(texts, 1):
        if any(_contains(t, kw) for kw in keywords):
            first_rr = 1.0 / rank
            break

    same_lang = sum(1 for l in langs if l == query_lang)
    same_lang_ratio = same_lang / len(langs) if langs else 0.0

    source_match = 0
    if expected_source:
        source_match = int(any(expected_source.lower() in c.source.lower()
                               for c in chunks))

    return RetrievalScore(
        hit_at_k=int(bool(found)),
        keyword_recall=round(keyword_recall, 3),
        first_hit_rr=round(first_rr, 3),
        same_lang_ratio=round(same_lang_ratio, 3),
        source_match=source_match,
    )


def score_language(answer_text: str, expected_lang: str) -> int:
    """1 if the answer is in the expected language, else 0."""
    from farmer import language_detector
    return int(language_detector.detect(answer_text).lang == expected_lang)


# Devanagari digits map onto Arabic ones, because a model answering in Marathi
# may write ५० where the source document says 50. They mean the same number and
# scoring them as different would be wrong.
_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NUMBER = __import__("re").compile(r"\d+(?:\.\d+)?")

# numbers that carry no factual weight and would only add noise
_TRIVIAL = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "100"}


def _numbers(text: str) -> set[str]:
    """Every meaningful number in a piece of text, script-normalised."""
    plain = (text or "").translate(_DEV_DIGITS)
    found = {n.lstrip("0") or "0" for n in _NUMBER.findall(plain)}
    return {n for n in found if n not in _TRIVIAL}


def score_grounding(answer_text: str, chunks) -> float:
    """
    What fraction of the numbers in the answer actually appear in the sources?

    This is the cheapest honest measure of hallucination we have, and it is the
    one that matters for this app. Advice to a farmer is mostly numbers — 50 kg
    of urea, 6,000 rupees, 72 hours — and a number the model invented is exactly
    the kind of mistake that costs a season. Prose can be waffly and harmless;
    a wrong dose is not.

    Returns 1.0 when every number is traceable to a retrieved chunk, and 1.0
    when the answer contains no numbers at all (nothing was claimed, so nothing
    was invented).
    """
    claimed = _numbers(answer_text)
    if not claimed:
        return 1.0
    context = " ".join(getattr(c, "text", "") for c in chunks)
    supported = _numbers(context)
    return round(len(claimed & supported) / len(claimed), 3)


def score_answer_keywords(answer_text: str, keywords: list[str]) -> float:
    """
    How much of what the farmer asked for actually made it into the answer.

    Retrieval recall says the right chunk was found. This says the model then
    used it. The two come apart more often than you would like.
    """
    if not keywords:
        return 0.0
    found = sum(1 for kw in keywords if _contains(answer_text, kw))
    return round(found / len(keywords), 3)


def aggregate(rows: list[dict]) -> dict:
    """Mean of numeric columns, grouped by nothing (caller groups first)."""
    if not rows:
        return {}
    keys = [k for k, v in rows[0].items() if isinstance(v, (int, float))]
    return {k: round(sum(r[k] for r in rows) / len(rows), 3) for k in keys}


def score_to_dict(s: RetrievalScore) -> dict:
    return asdict(s)
