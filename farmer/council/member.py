"""
One expert reading the documents.

Each seat gets the same question and the same retrieved chunks. What changes is
the brief, which is what makes the three opinions different instead of three
copies of the same paragraph.

Nothing in here is allowed to crash the app. If Groq times out or the free tier
rate-limits us, that seat is marked as failed and the council carries on with
the ones that answered.
"""

from __future__ import annotations

from dataclasses import dataclass

import config
from farmer.council import roles
from farmer.council.roles import Seat


@dataclass
class Opinion:
    seat: Seat
    text: str
    abstained: bool = False   # nothing in the documents for this seat
    failed: bool = False      # the call itself broke
    error: str = ""

    @property
    def spoke(self) -> bool:
        return not self.abstained and not self.failed and bool(self.text.strip())


def _looks_like_abstain(text: str) -> bool:
    """
    Models rarely give you the token on its own — you get "NO_INPUT." or
    "NO_INPUT (nothing here for me)". So we check the opening instead of
    demanding an exact match.
    """
    head = text.strip().strip("*_`\"' .").upper()
    return head.startswith(roles.ABSTAIN)


def consult(seat: Seat, question: str, context: str,
            answer_lang_name: str) -> Opinion:
    """Ask one seat for its opinion. Never raises."""
    from farmer import answer_writer   # imported here to keep the import one-way

    try:
        text = answer_writer.chat(
            system=roles.brief(seat, answer_lang_name),
            user=f"Context:\n{context}\n\nQuestion: {question}",
            temperature=config.COUNCIL_MEMBER_TEMPERATURE,
            max_tokens=config.COUNCIL_MEMBER_MAX_TOKENS,
        )
    except Exception as exc:
        return Opinion(seat=seat, text="", failed=True, error=str(exc)[:200])

    if _looks_like_abstain(text):
        return Opinion(seat=seat, text="", abstained=True)
    return Opinion(seat=seat, text=text.strip())


def transcript(opinions: list[Opinion]) -> str:
    """
    Lay the opinions out for the chairman to read.

    Quiet and failed seats are left out on purpose. If the chairman sees an
    empty opinion it tends to read it as disagreement and marks the agreement
    down for no reason.
    """
    blocks = []
    for op in opinions:
        if op.spoke:
            blocks.append(f"--- {op.seat.title} ---\n{op.text}")
    return "\n\n".join(blocks)
