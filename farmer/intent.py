"""
What is the farmer actually asking for?

The synopsis promises that the system "identifies the language and intent".
Language detection lives in language_detector.py; this is the other half.

It matters because not every question should go to the documents. "What is
onion selling for today?" cannot be answered from a PDF -- the answer is in the
live price feed, and retrieving a document about onion storage and generating a
confident paragraph from it would be worse than useless. Likewise "will it rain
tomorrow" belongs to the weather API, not the corpus.

So we route:

    price    -> the mandi feed
    weather  -> the forecast
    spray    -> the hourly spray window
    scheme   -> documents, but the Scheme Officer seat matters most
    advice   -> documents (the default: agronomy questions)

It is deliberately a keyword matcher and not a model call. Three reasons: it
runs in under a millisecond so nothing waits on it, it costs nothing on a free
tier that is already carrying four calls per question, and when it gets
something wrong you can see exactly which word did it and fix that word. A
classifier that is wrong for reasons nobody can inspect is worse here than a
simple one that is wrong for visible reasons.

Every keyword is listed in all three languages, because a Marathi speaker asking
about price says "भाव", not "price".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

PRICE = "price"
WEATHER = "weather"
SPRAY = "spray"
SCHEME = "scheme"
ADVICE = "advice"

# Ordered: the first intent with a match wins. Price sits above weather because
# "what is the rate today" is far more often about the mandi than the sky.
KEYWORDS: dict[str, tuple[str, ...]] = {
    PRICE: (
        "price", "rate", "mandi", "market", "sell", "selling", "quintal",
        "msp", "bhav", "auction",
        "भाव", "किंमत", "बाजार", "मंडी", "विक्री", "विकाव", "क्विंटल", "दर",
        "कीमत", "मंडी भाव", "बेच", "बिक्री",
    ),
    SPRAY: (
        "spray", "spraying", "pesticide", "fungicide", "insecticide", "drift",
        "फवारणी", "फवार", "कीटकनाशक", "बुरशीनाशक", "औषध",
        "छिड़काव", "छिडकाव", "कीटनाशक", "दवा",
    ),
    WEATHER: (
        "weather", "rain", "rainfall", "forecast", "temperature", "humidity",
        "wind", "storm", "hail", "frost", "drought", "monsoon",
        "हवामान", "पाऊस", "पाउस", "तापमान", "आर्द्रता", "वारा", "गारपीट",
        "मौसम", "बारिश", "बरसात", "ओलावृष्टि", "पूर्वानुमान", "नमी", "हवा",
    ),
    SCHEME: (
        "scheme", "subsidy", "yojana", "pm-kisan", "pmkisan", "pmfby",
        "insurance", "eligible", "eligibility", "apply", "application",
        "document", "loan", "kcc", "government", "grant",
        "योजना", "अनुदान", "विमा", "पात्र", "अर्ज", "कागदपत्र", "कर्ज",
        "सरकारी", "सबसिडी", "सब्सिडी", "बीमा", "पात्रता", "आवेदन",
        "दस्तावेज़", "दस्तावेज", "ऋण", "सरकार",
    ),
}

# What each intent means for the app: whether the corpus can answer it at all,
# and which screen holds the real answer.
ROUTES = {
    PRICE:   {"needs_documents": False, "screen": "market",
              "why": "prices change daily; the documents cannot know today's rate"},
    WEATHER: {"needs_documents": False, "screen": "today",
              "why": "the forecast is live data, not something in a document"},
    SPRAY:   {"needs_documents": True, "screen": "today",
              "why": "the safe hours are computed from the hourly forecast"},
    SCHEME:  {"needs_documents": True, "screen": "ask",
              "why": "scheme rules are in the documents"},
    ADVICE:  {"needs_documents": True, "screen": "ask",
              "why": "agronomy questions are answered from the documents"},
}


@dataclass
class Intent:
    name: str
    matched: str = ""        # the word that decided it, for debugging
    confident: bool = False  # False means we fell back to the default

    @property
    def needs_documents(self) -> bool:
        return ROUTES[self.name]["needs_documents"]

    @property
    def screen(self) -> str:
        return ROUTES[self.name]["screen"]

    @property
    def why(self) -> str:
        return ROUTES[self.name]["why"]


def _fold(text: str) -> str:
    """
    Lowercase, drop accents and punctuation, keep Devanagari intact.

    Same reasoning as in question_bank: a matra is a combining mark, not a
    letter, so stripping it as punctuation destroys the Marathi word.
    """
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^\w\sऀ-ॿ]", " ", stripped)


def classify(question: str) -> Intent:
    """Work out what kind of question this is. Never raises."""
    haystack = _fold(question)
    if not haystack.strip():
        return Intent(ADVICE)

    for name, words in KEYWORDS.items():
        for word in words:
            needle = _fold(word).strip()
            if not needle:
                continue
            # word boundaries for Latin so "rate" does not match "generated";
            # substring for Devanagari, where inflection changes the ending
            if needle.isascii():
                if re.search(rf"\b{re.escape(needle)}\b", haystack):
                    return Intent(name, matched=word, confident=True)
            elif needle in haystack:
                return Intent(name, matched=word, confident=True)

    return Intent(ADVICE, confident=False)


# what to tell the farmer when their question belongs on another screen
REDIRECTS = {
    PRICE: {
        "en": "For today's actual prices, open the Market screen — these "
              "documents cannot know today's rate.",
        "hi": "आज के असली भाव के लिए बाज़ार स्क्रीन खोलें — दस्तावेज़ों में आज का "
              "भाव नहीं हो सकता।",
        "mr": "आजच्या खऱ्या भावासाठी बाजार स्क्रीन उघडा — कागदपत्रांत आजचा भाव "
              "असू शकत नाही.",
    },
    WEATHER: {
        "en": "For the live forecast, open the Today screen.",
        "hi": "ताज़ा मौसम जानकारी के लिए 'आज' स्क्रीन खोलें।",
        "mr": "ताज्या हवामानासाठी 'आज' स्क्रीन उघडा.",
    },
}


def redirect_note(intent: Intent, lang: str = "en") -> str:
    """One line telling the farmer where the real answer lives. May be empty."""
    return REDIRECTS.get(intent.name, {}).get(lang, "")
