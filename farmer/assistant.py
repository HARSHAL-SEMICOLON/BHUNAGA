"""
The assistant itself, with no screen attached.

Everything the Streamlit app does to answer a question happens here: detect the
language, work out the intent, retrieve, run the council, and hand back an
answer plus everything worth knowing about how it was produced.

Pulling this out of ui/ask.py is what makes WhatsApp and IVR possible. Those
channels are not a different assistant; they are the same one reached down a
different pipe. A channel's job is only to turn its own message format into a
question and turn an Answer back into its own reply format.

    Streamlit  ─┐
    WhatsApp   ─┼─►  assistant.ask()  ─►  retrieval ─► council ─► answer
    IVR call   ─┘

It also means the whole pipeline can be tested without Streamlit in the way,
which is how most of the tests for it are written.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import config
from farmer import answer_writer, intent as intents, language_detector, searcher

# a spoken answer down a phone line has to be much shorter than one on a screen
IVR_MAX_CHARS = 600


@dataclass
class Reply:
    text: str
    lang: str
    intent: str = "advice"
    redirect: str = ""                      # where the real answer lives, if elsewhere
    sources: list = field(default_factory=list)
    consensus: int | None = None            # council agreement, if it ran
    experts: int = 0                        # how many experts spoke
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.text) and not self.error


def ask(question: str, lang: str = "", profile=None) -> Reply:
    """
    Answer one question. Never raises — every caller is a channel.

    `lang` may be "" or "auto" to detect from the question, which is what the
    phone channels do, since a caller cannot set a preference in advance.
    """
    question = (question or "").strip()
    if not question:
        return Reply("", lang or "en", error="empty question")

    if lang not in config.SUPPORTED_LANGS:
        try:
            lang = language_detector.detect(question).lang
        except Exception:
            lang = config.DEFAULT_LANG

    intent = intents.classify(question)
    redirect = ("" if intent.needs_documents
                else intents.redirect_note(intent, lang))

    try:
        chunks = searcher.retrieve(question, query_lang=lang)
    except Exception as exc:
        return Reply("", lang, intent=intent.name,
                     error=f"search unavailable: {str(exc)[:120]}")

    if not chunks:
        return Reply(
            "I could not find anything about that in the documents I have.",
            lang, intent=intent.name, redirect=redirect)

    asked = question
    if profile is not None and getattr(profile, "summary", None):
        context = profile.summary()
        if context:
            asked = f"{question}\n\n(Farmer context: {context})"

    try:
        answer = answer_writer.generate(asked, query_lang=lang, chunks=chunks)
    except Exception as exc:
        return Reply("", lang, intent=intent.name,
                     error=f"could not write an answer: {str(exc)[:120]}")

    reply = Reply(
        text=answer.text, lang=lang, intent=intent.name, redirect=redirect,
        sources=[{"source": c.source, "lang": c.source_lang} for c in chunks],
    )
    if answer.council is not None:
        reply.consensus = answer.council.verdict.score
        reply.experts = len(answer.council.verdict.spoke)
    return reply


def for_text_channel(reply: Reply, max_chars: int = 1400) -> str:
    """
    Format a reply for WhatsApp or SMS.

    Sources are named because a farmer acting on advice should be able to say
    where it came from, and the consensus score is included when the experts
    disagreed — on a phone there is no panel to expand, so a low score has to
    be stated in words or it is invisible.
    """
    if not reply.ok:
        return reply.error or "Sorry, something went wrong. Please try again."

    parts = [reply.text.strip()]

    if reply.redirect:
        parts.append(reply.redirect)

    if reply.consensus is not None and reply.consensus < config.CONSENSUS_WEAK:
        parts.append("Note: the experts did not fully agree on this. Please "
                     "check with your local Krishi Sahayak before acting.")

    if reply.sources:
        named = list(dict.fromkeys(s["source"] for s in reply.sources))[:2]
        parts.append("Source: " + ", ".join(named))

    out = "\n\n".join(parts)
    return out if len(out) <= max_chars else out[:max_chars - 1].rstrip() + "…"


def for_voice_channel(reply: Reply) -> str:
    """
    Format a reply to be read down a phone line.

    Spoken text has different rules from written text. Citation markers, bullet
    characters and source filenames are meaningless out loud, and a long answer
    is impossible to follow with no way to look back, so it is cut short and the
    caller is invited to ask again.
    """
    import re

    if not reply.ok:
        return "Sorry, I could not answer that. Please try again."

    spoken = re.sub(r"\[\d+\]", "", reply.text)
    spoken = re.sub(r"[*_#`]+", "", spoken)
    spoken = re.sub(r"^\s*[-•]\s*", ". ", spoken, flags=re.MULTILINE)
    spoken = re.sub(r"\s+", " ", spoken).strip()

    if len(spoken) > IVR_MAX_CHARS:
        cut = spoken[:IVR_MAX_CHARS]
        # end on a sentence rather than mid-word
        stop = max(cut.rfind("."), cut.rfind("।"))
        spoken = (cut[:stop + 1] if stop > IVR_MAX_CHARS // 2 else cut).strip()
        spoken += " That is the short answer. Please call again for more detail."

    return spoken
