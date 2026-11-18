"""
What was said a moment ago.

Every question used to be answered cold. That is fine for the first one and
wrong for the second:

    "माझ्या कपाशीवर पांढरी माशी आहे"   -> a good answer about whitefly on cotton
    "डोस किती?"                        -> retrieved from scratch, no idea what
                                          "dose" refers to, answered about
                                          something else entirely

This module is the smallest thing that fixes that. It holds a bounded history
and answers two questions about it:

  is this a follow-up?   -- decided by rule, not by a model call
  what should we search? -- the follow-up, with the earlier subject attached

Why rules and not a model. The free tier this project runs on allows 200,000
tokens a day; spending a classification call on every question to discover that
most of them are standalone would be most of that budget. The intent router in
farmer/intent.py is keyword-based for the same reason, and both are honest
about being heuristics rather than pretending to understand.

Nothing here is a substitute for memory across sessions. Close the tab and this
is gone -- it is a conversation, not a profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# How much history is carried. Three turns is enough for "and the dose?" and
# the follow-up to that; beyond it, older turns are more likely to drag
# retrieval towards a subject the farmer has already moved on from.
MAX_TURNS = 3

# An answer is quoted back to the council only as a reminder of the subject,
# never in full -- the whole point is to spend few tokens.
ANSWER_EXCERPT = 400

# Words that point at something already said. This is the whole of the
# anaphora detection, and it is deliberately small: every entry has to be a
# word that is almost meaningless on its own.
BACK_REFERENCES = {
    # English
    "it", "its", "it's", "that", "this", "they", "them", "those", "these",
    "same", "above", "again", "instead", "both",
    # Hindi
    "इसका", "इसकी", "इसके", "इसे", "इसमें", "उसका", "उसकी", "उसके", "उसे",
    "उसमें", "यह", "वह", "ये", "वो", "इनका", "उनका", "वही", "इसी", "उसी",
    # Marathi
    "त्याचा", "त्याची", "त्याचे", "त्यात", "त्याला", "याचा", "याची", "याचे",
    "यात", "याला", "ते", "तो", "ती", "हे", "हा", "ही", "तेच", "तेवढे", "तसेच",
}

# A question this short, with history behind it, is a fragment rather than a
# question. Four words would swallow real standalone questions like
# "गव्हासाठी किती युरिया" (3 words); three is the safe side of that line.
FRAGMENT_WORDS = 3


@dataclass(frozen=True)
class Turn:
    question: str
    answer: str = ""
    lang: str = "en"


@dataclass
class History:
    """A short, bounded conversation. Not persisted anywhere."""

    turns: list[Turn] = field(default_factory=list)

    def add(self, question: str, answer: str = "", lang: str = "en") -> None:
        question = (question or "").strip()
        if not question:
            return
        self.turns.append(Turn(question, (answer or "").strip(), lang))
        # keep the tail, drop the head
        del self.turns[:-MAX_TURNS]

    @property
    def last(self) -> Turn | None:
        return self.turns[-1] if self.turns else None

    def is_follow_up(self, question: str) -> bool:
        """
        Does this question only make sense with the previous one?

        True when there is something to refer back to AND the question either
        points at it ("what about the dose for it?") or is too short to stand
        on its own ("डोस किती?"). Both tests are cheap and wrong sometimes;
        the cost of a false positive is a slightly wider search, which is a
        great deal cheaper than the cost of a false negative, which is an
        answer about the wrong crop.
        """
        if not self.turns:
            return False
        words = (question or "").split()
        if not words:
            return False
        if len(words) <= FRAGMENT_WORDS:
            return True
        lowered = {w.strip(".,?!।॥\"'()").lower() for w in words}
        return bool(lowered & BACK_REFERENCES)

    def expand(self, question: str) -> str:
        """
        The string to search with.

        The earlier question is appended rather than prepended so the current
        one still dominates the embedding -- the subject is what is being
        borrowed, not the whole of the previous turn.
        """
        if not self.is_follow_up(question):
            return question
        previous = self.last
        return f"{question} {previous.question}" if previous else question

    def context_block(self, question: str) -> str:
        """
        A few lines of prior conversation for the council, or "".

        Only attached to follow-ups. A standalone question gets nothing, which
        keeps the common case exactly as cheap as it was before.
        """
        if not self.is_follow_up(question) or not self.turns:
            return ""
        lines = []
        for turn in self.turns:
            lines.append(f"Farmer asked: {turn.question}")
            if turn.answer:
                excerpt = turn.answer[:ANSWER_EXCERPT]
                if len(turn.answer) > ANSWER_EXCERPT:
                    excerpt = excerpt.rstrip() + "…"
                lines.append(f"You answered: {excerpt}")
        return ("Earlier in this conversation:\n" + "\n".join(lines)
                + "\n\nThe farmer is now following up on that.")


def from_ui_history(items) -> History:
    """
    Build a History from the list ui/ask.py already keeps in session state.

    The screen stores dicts with q/answer/lang; this keeps that format as the
    single source of truth rather than maintaining a second copy that can
    drift out of step with what is on screen.
    """
    history = History()
    for item in (items or []):
        if isinstance(item, dict):
            history.add(item.get("q", ""), item.get("answer", ""),
                        item.get("lang", "en"))
    return history
