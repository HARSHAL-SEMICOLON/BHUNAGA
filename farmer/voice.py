"""
Let the farmer speak the question instead of typing it.

This is the part of the app that matters most for someone who cannot read or
write. Typing Devanagari on a phone is slow even for people who can; for
everyone else it is a wall. Speaking is not.

We send the recording to Whisper on Groq, which is the same free key the rest of
the app already uses, and which handles Hindi and Marathi. Nothing is stored --
the audio goes up, the text comes back, and the recording is dropped.

Whisper is happier when told which language to expect, so if the farmer has
picked one in their profile we pass it on. On "auto" we let Whisper decide and
then run our own detector over the result, because Whisper is good at hearing
Devanagari but not always right about which of the two languages it is.
"""

from __future__ import annotations

from dataclasses import dataclass

import config

# turbo is roughly ten times cheaper and faster than the full model, and the
# difference does not show on a short spoken question
WHISPER_MODEL = "whisper-large-v3-turbo"

# below this many characters it is almost always a cough or a stray tap
MIN_USEFUL_CHARS = 3


@dataclass
class Heard:
    text: str
    lang: str = ""       # what we think was spoken
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.text) and not self.error


def transcribe(audio_bytes: bytes, filename: str = "question.wav",
               lang_hint: str = "") -> Heard:
    """
    Turn a recording into text. Never raises -- the caller is a UI.

    `lang_hint` is "en", "hi", "mr" or "" for let-Whisper-decide.
    """
    if not audio_bytes:
        return Heard("", error="Nothing was recorded.")
    if not config.GROQ_API_KEY:
        return Heard("", error="GROQ_API_KEY is not set, so voice is off.")

    try:
        from groq import Groq
        client = Groq(api_key=config.GROQ_API_KEY)
        kwargs = {"file": (filename, audio_bytes), "model": WHISPER_MODEL}
        if lang_hint in config.SUPPORTED_LANGS:
            kwargs["language"] = lang_hint
        result = client.audio.transcriptions.create(**kwargs)
        text = (getattr(result, "text", "") or "").strip()
    except Exception as exc:
        return Heard("", error=f"Could not hear that: {str(exc)[:160]}")

    if len(text) < MIN_USEFUL_CHARS:
        return Heard("", error="That was too short to make out. Try again.")

    # Whisper reports Hindi for most Devanagari, so trust our own detector for
    # the hi/mr split -- telling those two apart is the whole point of this app.
    lang = lang_hint
    if not lang:
        try:
            from farmer import language_detector
            lang = language_detector.detect(text).lang
        except Exception:
            lang = ""

    return Heard(text=text, lang=lang)
