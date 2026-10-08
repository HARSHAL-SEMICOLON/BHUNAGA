"""
The council of experts.

Instead of one model answering alone, three experts read the same retrieved
documents from three different angles and a chairman merges what they say. The
point is not to sound clever — it is that a wrong number usually comes from one
seat only, and putting three of them side by side makes it visible instead of
letting it slip into the answer unchallenged.

    question + retrieved chunks
             │
      ┌──────┼──────┐
      ▼      ▼      ▼
   🌱 agro  💰 econ  📜 scheme        each may also stay quiet
      └──────┼──────┘
             ▼
        👨‍⚖️ chairman  ──►  merged answer + agreement score + clashes

Use it like this:

    result = council.deliberate(question, chunks, "Marathi")
    print(result.verdict.answer, result.verdict.score)
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import config
from farmer.council import agreement, chairman, member, roles
from farmer.council.chairman import Verdict
from farmer.council.member import Opinion
from farmer.council.roles import SEATS, Seat

__all__ = ["deliberate", "Council", "Opinion", "Verdict", "Seat", "SEATS",
           "agreement", "chairman", "member", "roles"]


@dataclass
class Council:
    """Everything that happened, so the app can show its working."""
    opinions: list[Opinion]
    verdict: Verdict

    @property
    def answer(self) -> str:
        return self.verdict.answer


def _format_context(chunks) -> str:
    """Same numbering the single-agent path uses, so [2] means [2] everywhere."""
    return "\n\n".join(
        f"[{i}] (source: {c.source}, lang: {c.source_lang})\n{c.text}"
        for i, c in enumerate(chunks, 1)
    )


def _gather(question: str, context: str, lang_name: str) -> list[Opinion]:
    """Ask every seat. In parallel unless the config says otherwise."""
    jobs = [(seat, question, context, lang_name) for seat in SEATS]

    if not config.COUNCIL_PARALLEL:
        return [member.consult(*job) for job in jobs]

    # three at once keeps the wait around one call instead of three. if the free
    # tier starts rate-limiting, set COUNCIL_PARALLEL = False in config.
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        return list(pool.map(lambda job: member.consult(*job), jobs))


def deliberate(question: str, chunks, answer_lang_name: str) -> Council:
    """
    Run one full round: three opinions, then the chairman.

    If fewer seats speak than COUNCIL_MIN_SPEAKERS — usually because the free
    tier rate-limited us — there is nothing to reach consensus about, so we
    raise and let the caller drop back to the plain single-agent answer.
    """
    context = _format_context(chunks)
    opinions = _gather(question, context, answer_lang_name)

    speakers = [op for op in opinions if op.spoke]
    if len(speakers) < config.COUNCIL_MIN_SPEAKERS:
        broken = "; ".join(op.error for op in opinions if op.failed)
        raise RuntimeError(f"no expert could answer ({broken or 'all abstained'})")

    # one lone speaker needs no chairman, and paying for a merge of one opinion
    # would be silly. we hand it straight through and say the vote was 1-of-3.
    if len(speakers) == 1:
        only = speakers[0]
        verdict = Verdict(
            answer=only.text,
            score=100,
            label="strong",
            basis=f"only the {only.seat.title} had anything to say",
            chairman_score=100,
            word_overlap=1.0,
            spoke=[only.seat.key],
            quiet=[op.seat.key for op in opinions if not op.spoke],
        )
        return Council(opinions=opinions, verdict=verdict)

    verdict = chairman.preside(question, opinions, answer_lang_name)
    return Council(opinions=opinions, verdict=verdict)
