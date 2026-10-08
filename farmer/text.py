"""
Every word the interface says, in all three languages.

The point of this app is that a farmer can use it in their own language. An app
that answers in Marathi but whose buttons all say "Calculate" and "Get prices"
has only done half the job, and the half it skipped is the half a farmer meets
first.

So every string lives here, keyed by a short name, and no screen is allowed to
hard-code English. Adding a language later means adding one more column, not
hunting through seven files.

    from farmer.text import t
    t("ask.button", "mr")   ->  "विचारा 🌾"

A missing translation falls back to English rather than crashing or showing a
raw key, because a half-translated screen is still usable and a broken one is
not.
"""

from __future__ import annotations

LANGS = ("en", "hi", "mr")
LANG_NAMES = {"en": "English", "hi": "हिंदी", "mr": "मराठी"}
FALLBACK = "en"

STRINGS: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------- nav
    "nav.home": {"en": "Home", "hi": "होम", "mr": "घर"},
    "nav.ask": {"en": "Ask", "hi": "पूछें", "mr": "विचारा"},
    "nav.today": {"en": "Today", "hi": "आज", "mr": "आज"},
    "nav.money": {"en": "Money", "hi": "पैसा", "mr": "पैसा"},
    "nav.market": {"en": "Market", "hi": "बाज़ार", "mr": "बाजार"},
    "nav.back": {"en": "Back", "hi": "वापस", "mr": "मागे"},

    # --------------------------------------------------------------- home
    "home.ask": {"en": "Ask a question", "hi": "सवाल पूछें",
                 "mr": "प्रश्न विचारा"},
    "home.today": {"en": "What to do today", "hi": "आज क्या करें",
                   "mr": "आज काय करावे"},
    "home.money": {"en": "Cost & profit", "hi": "लागत और मुनाफ़ा",
                   "mr": "खर्च आणि नफा"},
    "home.market": {"en": "Today's prices", "hi": "आज के भाव",
                    "mr": "आजचे भाव"},
    "home.tagline": {
        "en": "Ask about your farm in your own language.",
        "hi": "अपनी खेती के बारे में अपनी भाषा में पूछें।",
        "mr": "तुमच्या शेतीबद्दल तुमच्या भाषेत विचारा."},
    "home.why": {"en": "Why earthworms matter", "hi": "केंचुए क्यों ज़रूरी हैं",
                 "mr": "गांडूळ का महत्त्वाचे"},
    "home.friends": {"en": "Friends of the Farmer", "hi": "किसान के मित्र",
                     "mr": "शेतकऱ्याचे मित्र"},
    "home.soil": {"en": "Soil health", "hi": "मिट्टी का स्वास्थ्य",
                  "mr": "मातीचे आरोग्य"},

    # ---------------------------------------------------------------- ask
    "ask.head": {"en": "Ask your question", "hi": "अपना सवाल पूछें",
                 "mr": "तुमचा प्रश्न विचारा"},
    "ask.speak": {"en": "🎤 Speak your question", "hi": "🎤 अपना सवाल बोलें",
                  "mr": "🎤 तुमचा प्रश्न बोला"},
    "ask.type": {"en": "⌨️ Or type it here", "hi": "⌨️ या यहाँ लिखें",
                 "mr": "⌨️ किंवा इथे लिहा"},
    "ask.button": {"en": "Ask 🌾", "hi": "पूछें 🌾", "mr": "विचारा 🌾"},
    "ask.browse": {"en": "👆 Or tap a question", "hi": "👆 या कोई सवाल चुनें",
                   "mr": "👆 किंवा प्रश्न निवडा"},
    "ask.listening": {"en": "Listening…", "hi": "सुन रहे हैं…",
                      "mr": "ऐकत आहोत…"},
    "ask.thinking": {"en": "Finding the answer…", "hi": "उत्तर खोज रहे हैं…",
                     "mr": "उत्तर शोधत आहोत…"},
    "ask.panel": {"en": "Asking the three experts…",
                  "hi": "तीन विशेषज्ञों से पूछ रहे हैं…",
                  "mr": "तीन तज्ज्ञांना विचारत आहोत…"},
    "ask.sources": {"en": "Where this came from", "hi": "यह जानकारी कहाँ से आई",
                    "mr": "ही माहिती कुठून आली"},
    "ask.clear": {"en": "🗑️ Clear", "hi": "🗑️ साफ़ करें", "mr": "🗑️ पुसा"},
    "ask.empty": {"en": "Load the knowledge base from the sidebar first.",
                  "hi": "पहले साइडबार से जानकारी लोड करें।",
                  "mr": "आधी साइडबारमधून माहिती लोड करा."},
    "ask.nothing": {
        "en": "I could not find anything about that in the documents I have.",
        "hi": "मेरे पास मौजूद दस्तावेज़ों में इसके बारे में कुछ नहीं मिला।",
        "mr": "माझ्याकडील कागदपत्रांमध्ये याबद्दल काही सापडले नाही."},

    # -------------------------------------------------------------- today
    "today.head": {"en": "What should I do today?", "hi": "आज मुझे क्या करना चाहिए?",
                   "mr": "आज मी काय करावे?"},
    "today.place": {"en": "📍 Your village or town", "hi": "📍 आपका गाँव या शहर",
                    "mr": "📍 तुमचे गाव किंवा शहर"},
    "today.generate": {"en": "Get today's advice", "hi": "आज की सलाह लें",
                       "mr": "आजचा सल्ला घ्या"},
    "today.working": {"en": "Preparing your daily plan…",
                      "hi": "आपकी दैनिक योजना तैयार हो रही है…",
                      "mr": "तुमची दैनंदिन योजना तयार होत आहे…"},
    "today.hint": {
        "en": "Set your village and crops in the sidebar for advice that fits "
              "your farm.",
        "hi": "अपनी खेती के अनुसार सलाह के लिए साइडबार में गाँव और फ़सलें भरें।",
        "mr": "तुमच्या शेतीनुसार सल्ल्यासाठी साइडबारमध्ये गाव आणि पिके भरा."},
    "today.temp": {"en": "Temperature", "hi": "तापमान", "mr": "तापमान"},
    "today.humidity": {"en": "Humidity", "hi": "नमी", "mr": "आर्द्रता"},
    "today.rain": {"en": "Rain", "hi": "बारिश", "mr": "पाऊस"},
    "today.wind": {"en": "Wind", "hi": "हवा", "mr": "वारा"},
    "today.week": {"en": "Next 7 days", "hi": "अगले 7 दिन", "mr": "पुढील ७ दिवस"},

    # -------------------------------------------------------------- spray
    "spray.head": {"en": "When can I spray?", "hi": "छिड़काव कब करें?",
                   "mr": "फवारणी कधी करावी?"},
    "spray.why": {
        "en": "Wrong wind blows the spray off your field and rain washes it "
              "off. Both waste the money you spent on it.",
        "hi": "तेज़ हवा में दवा खेत से उड़ जाती है और बारिश उसे धो देती है। "
              "दोनों में आपका पैसा बर्बाद होता है।",
        "mr": "जोरदार वाऱ्यात औषध शेताबाहेर उडते आणि पाऊस ते धुऊन टाकतो. "
              "दोन्हीमध्ये तुमचे पैसे वाया जातात."},
    "spray.check": {"en": "Check spraying hours", "hi": "छिड़काव के घंटे देखें",
                    "mr": "फवारणीचे तास पहा"},
    "spray.good": {"en": "Good hours to spray", "hi": "छिड़काव के अच्छे घंटे",
                   "mr": "फवारणीसाठी चांगले तास"},
    "spray.none": {
        "en": "No good spraying hours in the next two days — wind or rain every "
              "daylight hour. Wait and check again tomorrow.",
        "hi": "अगले दो दिनों में छिड़काव का अच्छा समय नहीं है — हर समय हवा या "
              "बारिश है। कल फिर देखें।",
        "mr": "पुढील दोन दिवसांत फवारणीसाठी चांगला वेळ नाही — सतत वारा किंवा "
              "पाऊस आहे. उद्या पुन्हा पहा."},

    # --------------------------------------------------------------- soil
    "soil.head": {"en": "My soil", "hi": "मेरी मिट्टी", "mr": "माझी माती"},
    "soil.check": {"en": "Check my soil", "hi": "मेरी मिट्टी देखें",
                   "mr": "माझी माती पहा"},
    "soil.working": {"en": "Reading the soil map…", "hi": "मिट्टी का नक्शा पढ़ रहे हैं…",
                     "mr": "मातीचा नकाशा वाचत आहोत…"},
    "soil.texture": {"en": "Soil type", "hi": "मिट्टी का प्रकार",
                     "mr": "मातीचा प्रकार"},

    # -------------------------------------------------------------- money
    "money.head": {"en": "Cost & profit", "hi": "लागत और मुनाफ़ा",
                   "mr": "खर्च आणि नफा"},
    "money.crop": {"en": "Crop", "hi": "फ़सल", "mr": "पीक"},
    "money.area": {"en": "Area (acres)", "hi": "क्षेत्र (एकड़)",
                   "mr": "क्षेत्र (एकर)"},
    "money.yield": {"en": "Yield per acre", "hi": "प्रति एकड़ उपज",
                    "mr": "प्रति एकर उत्पादन"},
    "money.price": {"en": "Selling price", "hi": "बिक्री भाव",
                    "mr": "विक्री भाव"},
    "money.calculate": {"en": "Calculate", "hi": "गणना करें", "mr": "गणना करा"},
    "money.total": {"en": "Total cost", "hi": "कुल लागत", "mr": "एकूण खर्च"},
    "money.revenue": {"en": "Total income", "hi": "कुल आय", "mr": "एकूण उत्पन्न"},
    "money.profit": {"en": "Profit", "hi": "मुनाफ़ा", "mr": "नफा"},
    "money.gain": {"en": "gain", "hi": "फ़ायदा", "mr": "फायदा"},
    "money.loss": {"en": "loss", "hi": "नुक़सान", "mr": "तोटा"},

    # ------------------------------------------------------------- market
    "market.head": {"en": "Mandi prices", "hi": "मंडी भाव", "mr": "बाजार भाव"},
    "market.commodity": {"en": "Crop", "hi": "फ़सल", "mr": "पीक"},
    "market.state": {"en": "State", "hi": "राज्य", "mr": "राज्य"},
    "market.district": {"en": "District (optional)", "hi": "ज़िला (वैकल्पिक)",
                        "mr": "जिल्हा (ऐच्छिक)"},
    "market.get": {"en": "Get prices", "hi": "भाव देखें", "mr": "भाव पहा"},
    "market.working": {"en": "Fetching mandi prices…", "hi": "मंडी भाव ला रहे हैं…",
                       "mr": "बाजार भाव आणत आहोत…"},
    "market.live": {"en": "🟢 Live — today's reported prices",
                    "hi": "🟢 लाइव — आज के दर्ज भाव",
                    "mr": "🟢 थेट — आजचे नोंदवलेले भाव"},
    "market.cached": {"en": "🟡 Saved earlier — not today's rate",
                      "hi": "🟡 पहले सहेजा गया — आज का भाव नहीं",
                      "mr": "🟡 आधी जतन केलेले — आजचा भाव नाही"},
    "market.sample": {"en": "⚪ Example figures — NOT real prices",
                      "hi": "⚪ नमूना आँकड़े — असली भाव नहीं",
                      "mr": "⚪ नमुना आकडे — खरे भाव नाहीत"},
    "market.unit": {"en": "₹ per quintal", "hi": "₹ प्रति क्विंटल",
                    "mr": "₹ प्रति क्विंटल"},

    # ------------------------------------------------------------ sidebar
    "side.profile": {"en": "My details", "hi": "मेरी जानकारी", "mr": "माझी माहिती"},
    "side.name": {"en": "Name", "hi": "नाम", "mr": "नाव"},
    "side.village": {"en": "Village / City", "hi": "गाँव / शहर",
                     "mr": "गाव / शहर"},
    "side.district": {"en": "District", "hi": "ज़िला", "mr": "जिल्हा"},
    "side.crops": {"en": "My crops", "hi": "मेरी फ़सलें", "mr": "माझी पिके"},
    "side.soil": {"en": "Soil type", "hi": "मिट्टी का प्रकार",
                  "mr": "मातीचा प्रकार"},
    "side.land": {"en": "Land (acres)", "hi": "ज़मीन (एकड़)", "mr": "जमीन (एकर)"},
    "side.language": {"en": "Language", "hi": "भाषा", "mr": "भाषा"},
    "side.save": {"en": "💾 Save", "hi": "💾 सहेजें", "mr": "💾 जतन करा"},
    "side.saved": {"en": "Saved.", "hi": "सहेज लिया।", "mr": "जतन केले."},
    "side.kb": {"en": "Knowledge base", "hi": "जानकारी का भंडार",
                "mr": "माहितीचा संग्रह"},
    "side.load": {"en": "📚 Load sample knowledge", "hi": "📚 नमूना जानकारी लोड करें",
                  "mr": "📚 नमुना माहिती लोड करा"},
    "side.upload": {"en": "Add your own documents", "hi": "अपने दस्तावेज़ जोड़ें",
                    "mr": "तुमची कागदपत्रे जोडा"},
    "side.chunks": {"en": "pieces of information ready",
                    "hi": "जानकारी के टुकड़े तैयार",
                    "mr": "माहितीचे तुकडे तयार"},
    "side.kb_empty": {"en": "Empty — load the sample knowledge below.",
                      "hi": "खाली — नीचे से नमूना जानकारी लोड करें।",
                      "mr": "रिकामे — खालून नमुना माहिती लोड करा."},
    "side.council": {"en": "Council of experts", "hi": "विशेषज्ञ परिषद",
                     "mr": "तज्ज्ञ परिषद"},
    "side.council_on": {"en": "Ask three experts, not one",
                        "hi": "एक नहीं, तीन विशेषज्ञों से पूछें",
                        "mr": "एक नाही, तीन तज्ज्ञांना विचारा"},
    "side.advanced": {"en": "⚙️ Advanced", "hi": "⚙️ उन्नत", "mr": "⚙️ प्रगत"},

    # ------------------------------------------------------------ council
    "council.strong": {"en": "The experts agreed", "hi": "विशेषज्ञ सहमत हैं",
                       "mr": "तज्ज्ञ सहमत आहेत"},
    "council.partial": {"en": "Partly agreed", "hi": "आंशिक रूप से सहमत",
                        "mr": "अंशतः सहमत"},
    "council.split": {"en": "The experts did not agree",
                      "hi": "विशेषज्ञ असहमत हैं", "mr": "तज्ज्ञांमध्ये मतभेद"},
    "council.how": {"en": "🧑‍⚖️ How the council decided",
                    "hi": "🧑‍⚖️ परिषद ने कैसे तय किया",
                    "mr": "🧑‍⚖️ परिषदेने कसे ठरवले"},
    "council.clash": {"en": "They did not agree:", "hi": "वे सहमत नहीं थे:",
                      "mr": "त्यांच्यात मतभेद:"},
    "council.quiet": {
        "en": "Nothing in the documents for this expert — stayed quiet.",
        "hi": "इस विशेषज्ञ के लिए दस्तावेज़ों में कुछ नहीं — चुप रहे।",
        "mr": "या तज्ज्ञासाठी कागदपत्रांत काही नाही — गप्प राहिले."},
    "council.broke": {"en": "This expert could not be reached.",
                      "hi": "इस विशेषज्ञ से संपर्क नहीं हो सका।",
                      "mr": "या तज्ज्ञाशी संपर्क होऊ शकला नाही."},

    # -------------------------------------------------------- read aloud
    "speak.listen": {"en": "🔊 Listen", "hi": "🔊 सुनें", "mr": "🔊 ऐका"},
    "speak.stop": {"en": "⏹ Stop", "hi": "⏹ रोकें", "mr": "⏹ थांबवा"},
    "speak.novoice": {"en": "No matching voice on this device.",
                      "hi": "इस डिवाइस में उपयुक्त आवाज़ नहीं है।",
                      "mr": "या डिव्हाइसवर योग्य आवाज नाही."},
    "speak.unsupported": {"en": "This browser cannot read text aloud.",
                          "hi": "यह ब्राउज़र पाठ नहीं बोल सकता।",
                          "mr": "हा ब्राउझर मजकूर वाचू शकत नाही."},

    # -------------------------------------------------------------- shared
    "common.loading": {"en": "Working…", "hi": "काम चल रहा है…",
                       "mr": "काम सुरू आहे…"},
    "common.nokey": {
        "en": "The AI key is not set, so answers and voice are switched off.",
        "hi": "एआई कुंजी सेट नहीं है, इसलिए उत्तर और आवाज़ बंद हैं।",
        "mr": "एआय की सेट नाही, त्यामुळे उत्तरे आणि आवाज बंद आहेत."},
}


def t(key: str, lang: str = FALLBACK) -> str:
    """
    One string, in one language.

    An unknown key returns the key itself. That is deliberate: it shows up
    immediately on screen during development instead of silently rendering
    an empty label.
    """
    entry = STRINGS.get(key)
    if entry is None:
        return key
    return entry.get(lang) or entry.get(FALLBACK) or key


def resolve(language: str) -> str:
    """Turn a profile setting ("auto", "mr", nonsense) into a real language."""
    return language if language in LANGS else FALLBACK


def missing() -> dict[str, list[str]]:
    """
    Which strings are not translated yet. Used by the tests.

    Keeping this honest matters — a screen that silently falls back to English
    looks finished when it is not.
    """
    gaps: dict[str, list[str]] = {}
    for key, entry in STRINGS.items():
        absent = [lang for lang in LANGS if not entry.get(lang)]
        if absent:
            gaps[key] = absent
    return gaps
