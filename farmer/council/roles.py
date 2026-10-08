"""
Who sits on the council.

Asking one model the same question three times mostly gives you the same answer
three times, so that is not a real second opinion. Instead we give every seat a
different job. The agronomist worries about the crop, the economist worries
about the money, and the scheme officer worries about government help. All three
read the same retrieved documents, but each one is told to look at them from its
own angle.

A seat is also allowed to stay quiet. If the documents hold nothing for it, it
says NO_INPUT instead of making something up. That matters: a question like
"how much urea per acre" has nothing in it for the scheme officer, and a council
where everybody always talks is not really a council.
"""

from __future__ import annotations

from dataclasses import dataclass

# what a seat writes when the documents have nothing for it
ABSTAIN = "NO_INPUT"


@dataclass(frozen=True)
class Seat:
    key: str          # short id we use in code and in the UI
    title: str        # what we call it in English
    title_mr: str     # and in Marathi, for the app
    icon: str
    remit: str        # the one line that says what this seat is for
    looks_for: str    # the concrete things it should pull out of the context


AGRONOMIST = Seat(
    key="agronomist",
    title="Agronomist",
    title_mr="कृषी तज्ज्ञ",
    icon="🌱",
    remit="the crop itself — what to apply, how much, and when",
    looks_for=(
        "fertiliser names and doses per acre, sowing and harvest windows, "
        "spacing, irrigation, seed treatment, pests and diseases with their "
        "control, and soil requirements"
    ),
)

ECONOMIST = Seat(
    key="economist",
    title="Farm Economist",
    title_mr="अर्थ सल्लागार",
    icon="💰",
    remit="the money — what it costs, what it earns, and what can go wrong",
    looks_for=(
        "input costs, expected yield per acre, market and mandi prices, "
        "storage and wastage losses, and the risk of the decision going bad"
    ),
)

SCHEME_OFFICER = Seat(
    key="scheme_officer",
    title="Scheme Officer",
    title_mr="योजना अधिकारी",
    icon="📜",
    remit="government help — schemes, subsidy, eligibility and paperwork",
    looks_for=(
        "scheme names such as PM-Kisan or PMFBY, who is eligible, subsidy "
        "percentages and amounts, deadlines, documents needed, and where the "
        "farmer has to apply"
    ),
)

# the order here is the order the cards show up in the app
SEATS: tuple[Seat, ...] = (AGRONOMIST, ECONOMIST, SCHEME_OFFICER)

BY_KEY = {s.key: s for s in SEATS}


def brief(seat: Seat, answer_lang_name: str) -> str:
    """The system prompt for one seat. Same shape for all three, different job."""
    return (
        f"You are the {seat.title} on an advisory council for Indian farmers. "
        f"Your responsibility is {seat.remit}.\n"
        f"From the context below, pull out only what belongs to you: "
        f"{seat.looks_for}.\n"
        "Rules you must follow:\n"
        "1. Use ONLY the provided context. Never add numbers or scheme names "
        "that are not written there.\n"
        "2. Stay inside your remit. Another expert is covering the other parts, "
        "so do not answer their share of the question.\n"
        f"3. If the context has nothing that belongs to your remit, reply with "
        f"exactly {ABSTAIN} and nothing else. Staying quiet is a correct answer.\n"
        "4. Keep it to 4 short points or fewer. Every point must be something "
        "the farmer can actually go and do.\n"
        "5. Quote the source number like [2] after any figure you give.\n"
        f"Write in {answer_lang_name}."
    )


def chairman_brief(answer_lang_name: str) -> str:
    """
    The chairman's prompt.

    We ask for JSON because we need the agreement number and the list of
    clashes as data, not buried inside a paragraph. The parser is forgiving,
    so a stray code fence does not break the app.
    """
    return (
        "You are the Chairman of an advisory council for Indian farmers. "
        "Three experts have each given their opinion on the same question, "
        "reading the same source documents. Your job is not to add new advice "
        "of your own — it is to turn their notes into one answer the farmer "
        "can act on.\n"
        "Do this:\n"
        "- Merge the opinions into a single answer, ordered the way the farmer "
        "would actually do the work.\n"
        "- Where two experts state different figures or contradict each other, "
        "say so openly in the answer rather than silently picking one.\n"
        "- Drop anything no expert supported. Do not invent numbers.\n"
        "- An expert that stayed quiet is not a disagreement. Ignore it.\n"
        "Reply with JSON only, in exactly this shape:\n"
        "{\n"
        '  "answer": "the merged advice for the farmer",\n'
        '  "agreement": 0-100, how much the experts actually agreed,\n'
        '  "conflicts": ["short line per real disagreement, [] if none"],\n'
        '  "basis": "one line on what you leaned on most"\n'
        "}\n"
        f'The "answer", "conflicts" and "basis" fields must be written in '
        f"{answer_lang_name}. Output nothing outside the JSON object."
    )
