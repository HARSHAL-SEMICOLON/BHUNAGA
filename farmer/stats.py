"""
Honest numbers for a small evaluation.

With twelve questions in three languages there are thirty-six observations per
arm. At that size a bare "council scored 0.08 higher" is close to meaningless:
it could be three questions going either way. Reporting it as though it were a
measurement is the most common way a small study overstates itself.

So this module provides the two things that make a pilot defensible.

**Per-question wins and losses.** The arms answer the *same* questions, so the
comparison is paired. Counting how many questions each arm won is easy to read
and hard to misinterpret -- "the council was better on 7, worse on 5, the same
on 24" tells an examiner more than any single average.

**A paired bootstrap interval.** Resample the questions with replacement a few
thousand times, recompute the mean difference each time, and report the middle
95% of those differences. If that interval contains zero, the data does not
show a difference, and saying so plainly is a stronger result than pretending
otherwise.

Pure standard library. No scipy, in keeping with the rest of the project.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

BOOTSTRAP_ROUNDS = 5000
CONFIDENCE = 0.95


@dataclass
class Paired:
    metric: str
    n: int                      # questions answered by both arms
    mean_a: float
    mean_b: float
    delta: float                # b - a
    low: float                  # confidence interval on the delta
    high: float
    wins_b: int                 # questions where b beat a
    wins_a: int
    ties: int

    @property
    def significant(self) -> bool:
        """True when the interval misses zero. Not proof, but worth saying."""
        return self.low > 0 or self.high < 0

    def verdict(self, name_a: str, name_b: str) -> str:
        """One sentence a reader can quote without misrepresenting the data."""
        if self.n == 0:
            return f"{self.metric}: no questions answered by both arms."
        if not self.significant:
            return (f"{self.metric}: no reliable difference "
                    f"({self.delta:+.3f}, 95% CI [{self.low:+.3f}, "
                    f"{self.high:+.3f}], n={self.n}).")
        better = name_b if self.delta > 0 else name_a
        return (f"{self.metric}: {better} is better "
                f"({self.delta:+.3f}, 95% CI [{self.low:+.3f}, "
                f"{self.high:+.3f}], n={self.n}).")


def _percentile(values: list[float], fraction: float) -> float:
    """Linear-interpolated percentile. values must already be sorted."""
    if not values:
        return 0.0
    position = fraction * (len(values) - 1)
    low = int(position)
    high = min(low + 1, len(values) - 1)
    weight = position - low
    return values[low] * (1 - weight) + values[high] * weight


def compare(rows_a: list[dict], rows_b: list[dict], metric: str,
            key_fields: tuple = ("id", "lang"),
            rounds: int = BOOTSTRAP_ROUNDS, seed: int = 0) -> Paired:
    """
    Compare one metric across two arms, pairing on the same question.

    Rows missing the metric are dropped rather than counted as zero — a
    question that was never run is not a question the arm got wrong.
    """
    def index(rows):
        out = {}
        for row in rows:
            value = row.get(metric, "")
            if value in ("", None):
                continue
            try:
                out[tuple(row[f] for f in key_fields)] = float(value)
            except (TypeError, ValueError):
                continue
        return out

    left, right = index(rows_a), index(rows_b)
    shared = sorted(set(left) & set(right))
    if not shared:
        return Paired(metric, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0)

    diffs = [right[k] - left[k] for k in shared]
    n = len(shared)
    mean_a = sum(left[k] for k in shared) / n
    mean_b = sum(right[k] for k in shared) / n
    delta = sum(diffs) / n

    rng = random.Random(seed)       # seeded: the same data gives the same CI
    means = []
    for _ in range(rounds):
        resampled = [diffs[rng.randrange(n)] for _ in range(n)]
        means.append(sum(resampled) / n)
    means.sort()

    tail = (1 - CONFIDENCE) / 2
    return Paired(
        metric=metric, n=n, mean_a=round(mean_a, 3), mean_b=round(mean_b, 3),
        delta=round(delta, 3),
        low=round(_percentile(means, tail), 3),
        high=round(_percentile(means, 1 - tail), 3),
        wins_b=sum(1 for d in diffs if d > 0),
        wins_a=sum(1 for d in diffs if d < 0),
        ties=sum(1 for d in diffs if d == 0),
    )
