"""
The questions farmers actually ask, written out in all three languages.

Two jobs:

1. A farmer who cannot read still has to be able to ask something. So every
   question carries an icon and sits under a topic that also has an icon, and
   the app can show them as big tappable cards. Tap the picture, get the
   question -- no typing, no reading.

2. A farmer who can type gets these as suggestions while typing. Matching is
   done on all three languages at once, so typing "kanda" or "कांदा" or "onion"
   all find the onion questions.

Adding one is a one-liner: put a Q(...) in the right topic and it turns up in
the cards and the autocomplete straight away.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Q:
    icon: str
    en: str
    hi: str
    mr: str

    def text(self, lang: str) -> str:
        """The question in the farmer's language, English if we do not have it."""
        return {"hi": self.hi, "mr": self.mr}.get(lang) or self.en

    def all_text(self) -> str:
        """Every language joined up, for matching against."""
        return f"{self.en} {self.hi} {self.mr}"


@dataclass(frozen=True)
class Topic:
    key: str
    icon: str
    en: str
    hi: str
    mr: str
    questions: tuple[Q, ...]

    def label(self, lang: str) -> str:
        return {"hi": self.hi, "mr": self.mr}.get(lang) or self.en


TOPICS: tuple[Topic, ...] = (
    Topic(
        key="crop", icon="🌾", en="My crop", hi="मेरी फसल", mr="माझे पीक",
        questions=(
            Q("💊", "How much urea per acre for wheat?",
              "गेहूं के लिए प्रति एकड़ कितनी यूरिया चाहिए?",
              "गव्हासाठी प्रति एकर किती युरिया लागते?"),
            Q("🌱", "When should I sow soybean?",
              "सोयाबीन की बुवाई कब करनी चाहिए?",
              "सोयाबीनची पेरणी कधी करावी?"),
            Q("🐛", "How do I control pests on cotton?",
              "कपास में कीट नियंत्रण कैसे करें?",
              "कपाशीवरील किडींचे नियंत्रण कसे करावे?"),
            Q("💧", "How often should I water sugarcane?",
              "गन्ने को कितनी बार पानी देना चाहिए?",
              "ऊसाला किती वेळा पाणी द्यावे?"),
            Q("📦", "How should I store onions after harvest?",
              "कटाई के बाद प्याज़ का भंडारण कैसे करें?",
              "कांदा काढणीनंतर साठवणूक कशी करावी?"),
            Q("🍇", "How do I care for a grape vineyard?",
              "अंगूर के बाग की देखभाल कैसे करें?",
              "द्राक्ष बागेची काळजी कशी घ्यावी?"),
        ),
    ),
    Topic(
        key="soil", icon="🟫", en="Soil & compost", hi="मिट्टी और खाद",
        mr="माती आणि खत",
        questions=(
            Q("🪱", "How do earthworms improve my soil?",
              "केंचुए मिट्टी को कैसे बेहतर बनाते हैं?",
              "गांडूळ माती कशी सुधारतात?"),
            Q("🍂", "How do I make vermicompost at home?",
              "घर पर वर्मीकम्पोस्ट कैसे बनाएं?",
              "घरच्या घरी गांडूळखत कसे तयार करावे?"),
            Q("🧪", "How do I read my soil health card?",
              "मृदा स्वास्थ्य कार्ड कैसे पढ़ें?",
              "मृदा आरोग्य पत्रिका कशी वाचावी?"),
            Q("⚖️", "Is my soil too acidic or too alkaline?",
              "मेरी मिट्टी अम्लीय है या क्षारीय?",
              "माझी माती आम्लयुक्त आहे की क्षारयुक्त?"),
        ),
    ),
    Topic(
        key="money", icon="💰", en="Cost & profit", hi="लागत और मुनाफ़ा",
        mr="खर्च आणि नफा",
        questions=(
            Q("🧾", "What does it cost to grow one acre of onion?",
              "एक एकड़ प्याज़ उगाने में कितना खर्च आता है?",
              "एक एकर कांदा पिकवण्यासाठी किती खर्च येतो?"),
            Q("📈", "Which crop gives the best profit on 2 acres?",
              "दो एकड़ में कौन सी फसल सबसे ज़्यादा मुनाफ़ा देती है?",
              "दोन एकरात कोणते पीक सर्वाधिक नफा देते?"),
            Q("🏷️", "When is the best time to sell my crop?",
              "फसल बेचने का सबसे अच्छा समय कब है?",
              "पीक विकण्यासाठी सर्वोत्तम वेळ कोणती?"),
        ),
    ),
    Topic(
        key="scheme", icon="🏛️", en="Government help", hi="सरकारी मदद",
        mr="सरकारी मदत",
        questions=(
            Q("💵", "Am I eligible for PM-Kisan?",
              "क्या मैं पीएम-किसान के लिए पात्र हूँ?",
              "मी पीएम-किसानसाठी पात्र आहे का?"),
            Q("🛡️", "How do I claim crop insurance under PMFBY?",
              "पीएमएफबीवाई में फसल बीमा का दावा कैसे करें?",
              "पीएमएफबीवाय अंतर्गत पीक विम्याचा दावा कसा करावा?"),
            Q("💧", "What subsidy is there for drip irrigation?",
              "ड्रिप सिंचाई पर कितनी सब्सिडी मिलती है?",
              "ठिबक सिंचनासाठी किती अनुदान मिळते?"),
            Q("📄", "Which documents do I need to apply?",
              "आवेदन के लिए कौन से दस्तावेज़ चाहिए?",
              "अर्जासाठी कोणती कागदपत्रे लागतात?"),
        ),
    ),
    Topic(
        key="weather", icon="🌦️", en="Weather", hi="मौसम", mr="हवामान",
        questions=(
            Q("🌧️", "Will rain damage my standing crop?",
              "क्या बारिश से खड़ी फसल को नुकसान होगा?",
              "पावसामुळे उभ्या पिकाचे नुकसान होईल का?"),
            Q("☀️", "How do I protect my crop from heat?",
              "गर्मी से फसल को कैसे बचाएं?",
              "उष्णतेपासून पिकाचे संरक्षण कसे करावे?"),
            Q("🌊", "What should I do if my field floods?",
              "खेत में पानी भर जाए तो क्या करें?",
              "शेतात पाणी साचल्यास काय करावे?"),
        ),
    ),
)

BY_KEY = {t.key: t for t in TOPICS}


def all_questions() -> list[Q]:
    return [q for t in TOPICS for q in t.questions]


# Keep the Devanagari block explicitly. Python's \w only covers letters, and a
# matra like "ा" is a combining mark, not a letter — so a plain [^\w\s] strips
# every matra out of a Marathi word and leaves you with loose consonants.
# "कांदा" would become "क द", which matches nothing.
_PUNCT = re.compile(r"[^\w\sऀ-ॿ]", re.UNICODE)


def _fold(text: str) -> str:
    """
    Flatten text so near-misses still match.

    Drops accents (café → cafe) and the nukta, removes punctuation, lowercases.
    Matras are deliberately kept, for the reason above.
    """
    decomposed = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _PUNCT.sub(" ", stripped)


# Plenty of farmers type Marathi and Hindi words using English letters, because
# that is what the phone keyboard opens on. So "kanda" has to find the onion
# questions. Each hint expands into words that genuinely appear in the bank --
# there is no point mapping "yojana" to "scheme" if no question says "scheme".
ROMAN_HINTS = {
    "kanda": "onion कांदा", "kande": "onion कांदा", "pyaz": "onion प्याज़",
    "gehu": "wheat गेहूं", "gahu": "wheat गव्हा", "kapus": "cotton कपाशी",
    "kapas": "cotton कपास", "ganna": "sugarcane गन्ना", "us": "sugarcane ऊस",
    "draksha": "grape द्राक्ष", "angur": "grape अंगूर",
    "khat": "urea fertiliser खत", "khad": "urea fertiliser खाद",
    "urea": "urea यूरिया युरिया",
    "pani": "water irrigation पाणी", "paus": "rain पाऊस", "barish": "rain बारिश",
    "kid": "pest किड", "keet": "pest कीट", "mati": "soil माती",
    "paisa": "cost money पैसा", "nafa": "profit नफा",
    "bhav": "price sell भाव विक बेच", "bhaav": "price sell भाव विक बेच",
    "yojana": "subsidy insurance scheme योजना",
    "sarkar": "subsidy insurance kisan सरकार",
    "vima": "insurance विमा", "bima": "insurance बीमा",
    "kenchua": "earthworm केंचुआ", "bhunaga": "earthworm soil भुनागा",
}


def suggest(typed: str, lang: str = "en", limit: int = 6) -> list[Q]:
    """
    Questions that match what the farmer has typed so far.

    Empty box gives the most common questions rather than nothing, because an
    empty dropdown teaches nobody what this app can do.
    """
    typed = (typed or "").strip()
    if not typed:
        return [t.questions[0] for t in TOPICS][:limit]

    needle = _fold(typed)
    words = [w for w in needle.split() if len(w) > 1]
    for w in list(words):
        if w in ROMAN_HINTS:
            words.extend(_fold(ROMAN_HINTS[w]).split())
    if not words:
        return []

    scored = []
    for q in all_questions():
        hay = _fold(q.all_text())
        hits = sum(1 for w in words if w in hay)
        if not hits:
            continue
        # a question that starts with what they typed is almost certainly the
        # one they were reaching for, so push it up
        head = 1 if _fold(q.text(lang)).startswith(needle[:6]) else 0
        scored.append((hits + head, q))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [q for _, q in scored[:limit]]
