"""
How much did the experts actually agree?

The chairman gives us an agreement number, but that number is the model marking
its own homework. So we also measure the overlap ourselves, without any model
involved: take the words each expert used, throw away the filler words, and see
how much the sets have in common.

It is a blunt measure and we do not pretend otherwise. Two experts can say the
same thing in different words and score low. But it is honest, it costs nothing,
and if it disagrees badly with the chairman's own number that is worth seeing.
It works on Devanagari the same as on Latin because it only ever splits on
spaces and punctuation.
"""

from __future__ import annotations

import re
from itertools import combinations

# filler words in the three languages. these show up in every answer, so leaving
# them in would make any two answers look similar.
STOPWORDS = {
    # English
    "the", "and", "for", "with", "that", "this", "from", "your", "you", "are",
    "can", "will", "per", "use", "not", "but", "any", "all", "its", "has",
    "have", "should", "must", "when", "what", "how", "also", "more", "than",
    # Hindi
    "और", "के", "का", "की", "को", "में", "से", "है", "हैं", "पर", "यह", "वह",
    "एक", "लिए", "कर", "करें", "होता", "होती", "अगर", "तो", "भी", "साथ",
    # Marathi
    "आणि", "आहे", "आहेत", "करा", "करावी", "करावे", "साठी", "मध्ये", "पासून",
    "ची", "चा", "चे", "ला", "ते", "तो", "ही", "हे", "एक", "किंवा", "पण",
}

_SPLIT = re.compile(r"[^\wऀ-ॿ]+", re.UNICODE)


def _bag(text: str) -> set[str]:
    """The meaningful words in one opinion, as a set."""
    words = _SPLIT.split(text.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def overlap(texts: list[str]) -> float:
    """
    Average Jaccard overlap over every pair of opinions, 0.0 to 1.0.

    One opinion means nothing to compare against, so we return 1.0 — a lone
    expert never contradicts anybody.
    """
    bags = [b for b in (_bag(t) for t in texts) if b]
    if len(bags) < 2:
        return 1.0

    scores = []
    for a, b in combinations(bags, 2):
        union = a | b
        if union:
            scores.append(len(a & b) / len(union))
    return sum(scores) / len(scores) if scores else 1.0


def blend(chairman_score: int, word_overlap: float) -> int:
    """
    One number out of the two.

    We lean on the chairman because it actually read the opinions and understood
    them, and use the word overlap as a check on it. Weights are 70/30; the word
    overlap is scaled up because raw Jaccard on short text sits low even when two
    experts plainly agree.
    """
    measured = min(1.0, word_overlap * 2.2) * 100
    return int(round(0.7 * chairman_score + 0.3 * measured))


def label(score: int, strong: int, weak: int) -> str:
    """Turn the number into a word the farmer can read."""
    if score >= strong:
        return "strong"
    if score >= weak:
        return "partial"
    return "split"
