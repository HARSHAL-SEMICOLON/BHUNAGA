"""
The chairman.

Reads what the three experts wrote and turns it into one answer, plus a number
saying how much they agreed and a list of the places where they clashed.

We ask for JSON so the agreement number and the clashes come back as data we can
put on screen. Models are not reliable about JSON, so the parser here is
deliberately forgiving, and if it still fails we fall back to using the raw text
as the answer. A messy answer beats a crash.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import config
from farmer.council import agreement, member, roles

_FENCE = re.compile(r"^```(?:json)?|```$", re.MULTILINE)


@dataclass
class Verdict:
    answer: str
    score: int                              # 0-100, blended
    label: str                              # strong / partial / split
    conflicts: list[str] = field(default_factory=list)
    basis: str = ""
    chairman_score: int = 0                 # what the chairman claimed
    word_overlap: float = 0.0               # what we measured ourselves
    spoke: list[str] = field(default_factory=list)   # seat keys that answered
    quiet: list[str] = field(default_factory=list)   # seat keys that abstained
    fell_back: bool = False                 # true if the JSON did not parse


def _extract_json(raw: str) -> dict | None:
    """Pull the JSON object out, even if the model wrapped it in chatter."""
    cleaned = _FENCE.sub("", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # take everything between the first { and the last } and retry
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _as_int(value, default: int = 50) -> int:
    """agreement comes back as 82, "82", or "82%" depending on the model's mood."""
    try:
        return max(0, min(100, int(float(str(value).strip().rstrip("%")))))
    except (TypeError, ValueError):
        return default


def _as_lines(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def preside(question: str, opinions: list[member.Opinion],
            answer_lang_name: str) -> Verdict:
    """Merge the opinions into one verdict."""
    from farmer import answer_writer   # deferred, same reason as in member.py

    spoke = [op for op in opinions if op.spoke]
    quiet = [op.seat.key for op in opinions if not op.spoke]

    measured = agreement.overlap([op.text for op in spoke])
    notes = member.transcript(opinions)

    raw = answer_writer.chat(
        system=roles.chairman_brief(answer_lang_name),
        user=f"Question: {question}\n\nExpert opinions:\n{notes}",
        temperature=config.CHAIRMAN_TEMPERATURE,
        max_tokens=config.CHAIRMAN_MAX_TOKENS,
        model=config.CHAIRMAN_MODEL,
    )

    parsed = _extract_json(raw)
    if parsed is None:
        # the model ignored us and wrote prose. use it, but say so, and trust
        # only the number we measured ourselves.
        claimed = int(round(measured * 100))
        score = agreement.blend(claimed, measured)
        return Verdict(
            answer=raw.strip(),
            score=score,
            label=agreement.label(score, config.CONSENSUS_STRONG,
                                  config.CONSENSUS_WEAK),
            chairman_score=claimed,
            word_overlap=measured,
            spoke=[op.seat.key for op in spoke],
            quiet=quiet,
            fell_back=True,
        )

    claimed = _as_int(parsed.get("agreement"))
    score = agreement.blend(claimed, measured)
    return Verdict(
        answer=str(parsed.get("answer", "")).strip() or raw.strip(),
        score=score,
        label=agreement.label(score, config.CONSENSUS_STRONG,
                              config.CONSENSUS_WEAK),
        conflicts=_as_lines(parsed.get("conflicts")),
        basis=str(parsed.get("basis", "")).strip(),
        chairman_score=claimed,
        word_overlap=measured,
        spoke=[op.seat.key for op in spoke],
        quiet=quiet,
    )
