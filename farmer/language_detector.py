"""
Find the language of a piece of text: English, Hindi or Marathi.

Hindi and Marathi are written with the same letters, so we cannot guess by the
letters alone. We use a small ready-made tool called "lingua" that was trained
to tell languages apart. It needs no download and no compiler, so it works on
any computer.
"""

from __future__ import annotations

from dataclasses import dataclass

import config

_detector = None  # the language tool. we load it only when we need it


@dataclass
class LangResult:
    lang: str          # one of config.SUPPORTED_LANGS (post-fallback)
    confidence: float  # 0..1
    raw_lang: str      # detector's raw choice ("und" if none)


# map lingua Language enum names -> our codes
_LINGUA_TO_CODE = {"ENGLISH": "en", "HINDI": "hi", "MARATHI": "mr"}


def _load():
    global _detector
    if _detector is not None:
        return _detector
    from lingua import Language, LanguageDetectorBuilder
    _detector = LanguageDetectorBuilder.from_languages(
        Language.ENGLISH, Language.HINDI, Language.MARATHI
    ).build()
    return _detector


def detect(text: str) -> LangResult:
    """Detect language of `text`, restricted to en/hi/mr.

    Falls back to config.DEFAULT_LANG when the text is empty, no language is
    returned, or the top confidence is below config.LANGID_MIN_CONFIDENCE.
    """
    text = (text or "").replace("\n", " ").strip()
    if not text:
        return LangResult(config.DEFAULT_LANG, 0.0, "und")

    detector = _load()
    ranked = detector.compute_language_confidence_values(text)
    if not ranked:
        return LangResult(config.DEFAULT_LANG, 0.0, "und")

    top = ranked[0]
    raw = _LINGUA_TO_CODE.get(top.language.name, config.DEFAULT_LANG)
    conf = float(top.value)

    lang = raw if conf >= config.LANGID_MIN_CONFIDENCE else config.DEFAULT_LANG
    return LangResult(lang=lang, confidence=conf, raw_lang=raw)


if __name__ == "__main__":
    samples = [
        "How much urea per acre for wheat?",
        "गेहूं के लिए प्रति एकड़ कितनी यूरिया चाहिए?",   # Hindi
        "गव्हासाठी प्रति एकर किती युरिया लागते?",        # Marathi
    ]
    for s in samples:
        r = detect(s)
        print(f"{r.lang:3} ({r.confidence:.2f})  raw={r.raw_lang:4}  {s}")
