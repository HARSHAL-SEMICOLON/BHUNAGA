"""
The control arm: the same model, asked the same thing, several times.

Why this file exists
--------------------
The council makes four model calls where a single answer makes one. If the
council scores better, that on its own proves nothing -- four calls might
simply beat one call, whatever you do with them. Expert roles, a chairman,
structured disagreement: none of it is demonstrated until it is compared
against the cheapest thing that also costs four calls.

So this is that cheapest thing. One prompt, the same prompt the single-agent
path uses, sampled N times at a temperature high enough that the samples
actually differ, and then the most typical one is kept. No roles, no chairman,
no structure at all -- just repetition.

Three outcomes, all of them worth reporting:

  council > self-consistency   the structure is doing real work
  council ≈ self-consistency   the gain is from extra sampling, not from roles
  council < self-consistency   the structure is costing you something

The second is the result most multi-agent papers would have found if they had
run this arm, which is exactly why it belongs here.

How the winner is picked
------------------------
Self-consistency on maths problems takes a majority vote, because answers are
short and either identical or not. Free-text agricultural advice has no two
identical answers, so instead we take the **medoid**: the sample that is most
like all the others. If three samples say 50 kg of urea and one says 95, the
odd one out has low overlap with everything and loses. That is the same logic
as a majority vote, applied to prose.

The overlap measure is the one the council already uses, deliberately -- the
two arms are then scored by exactly the same yardstick.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import config
from farmer.council import agreement


@dataclass
class Sample:
    text: str
    typicality: float = 0.0     # mean word overlap with the other samples
    failed: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.text.strip()) and not self.failed


@dataclass
class Consensus:
    """Shaped to line up with council.Verdict, so evaluate.py treats them alike."""
    answer: str
    score: int                                  # 0-100, how much the samples agreed
    label: str = "partial"
    samples: list = field(default_factory=list)
    picked: int = 0                             # which sample won
    word_overlap: float = 0.0

    @property
    def spoke(self) -> list:
        """How many calls produced a usable answer. Mirrors Verdict.spoke."""
        return [i for i, s in enumerate(self.samples) if s.ok]


def _typicality(texts: list[str]) -> list[float]:
    """
    For each text, its mean overlap with every other text.

    The medoid is whichever scores highest: the answer sitting closest to the
    middle of the cloud. An invented figure drags a sample away from the others
    and costs it the vote.
    """
    count = len(texts)
    if count < 2:
        return [1.0] * count

    totals = [0.0] * count
    for i, j in combinations(range(count), 2):
        pair = agreement.overlap([texts[i], texts[j]])
        totals[i] += pair
        totals[j] += pair
    return [total / (count - 1) for total in totals]


def answer(query: str, chunks, answer_lang_name: str,
           samples: int | None = None) -> Consensus:
    """
    Sample the same prompt several times and keep the most typical answer.

    Raises only if every sample failed -- the caller can then fall back the
    same way it would for a broken council.
    """
    from farmer import answer_writer

    wanted = samples or config.SELFCONS_SAMPLES
    context = answer_writer._format_context(chunks)
    system = answer_writer._system_prompt(answer_lang_name)
    user = f"Context:\n{context}\n\nQuestion: {query}"

    drawn: list[Sample] = []
    for _ in range(wanted):
        try:
            # Temperature matters here. At the single-agent default of 0.2 the
            # samples come back nearly identical, the medoid is meaningless and
            # the arm is just a slower single answer. We use the same
            # temperature the council's experts run at, so the two arms differ
            # in structure and not in how adventurous the model is allowed to be.
            text = answer_writer.chat(
                system=system, user=user,
                temperature=config.SELFCONS_TEMPERATURE,
            )
            drawn.append(Sample(text=text.strip()))
        except Exception as exc:
            drawn.append(Sample(text="", failed=True, error=str(exc)[:200]))

    usable = [s for s in drawn if s.ok]
    if not usable:
        broken = "; ".join(s.error for s in drawn if s.failed)
        raise RuntimeError(f"no sample succeeded ({broken or 'all empty'})")

    scores = _typicality([s.text for s in usable])
    for sample, score in zip(usable, scores):
        sample.typicality = round(score, 3)

    best = max(range(len(usable)), key=lambda i: scores[i])
    measured = sum(scores) / len(scores)

    # Scaled the same way the council scales its own measured overlap, so a
    # consensus score of 70 means the same thing in both columns of the report.
    score = int(round(min(1.0, measured * 2.2) * 100))

    return Consensus(
        answer=usable[best].text,
        score=score,
        label=agreement.label(score, config.CONSENSUS_STRONG,
                              config.CONSENSUS_WEAK),
        samples=drawn,
        picked=best,
        word_overlap=round(measured, 3),
    )
