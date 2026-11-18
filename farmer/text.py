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
    "nav.diagnose": {"en": "Crop check", "hi": "फसल जाँच",
                     "mr": "पीक तपासणी"},

    # ------------------------------------------------- crop photo check
    "diag.head": {"en": "Photograph a sick plant",
                  "hi": "बीमार पौधे की फोटो लें",
                  "mr": "आजारी झाडाचा फोटो काढा"},
    "diag.hint": {
        "en": "Get close. Fill the frame with the affected leaf, in daylight, "
              "without shadow. A clear photo of one leaf is worth more than a "
              "photo of the whole field.",
        "hi": "पास से लें। प्रभावित पत्ते से पूरा फ्रेम भरें, दिन के उजाले में, "
              "बिना छाया के। पूरे खेत की फोटो से एक पत्ते की साफ़ फोटो ज़्यादा "
              "काम की है।",
        "mr": "जवळून काढा. प्रभावित पानाने संपूर्ण फ्रेम भरा, दिवसाच्या उजेडात, "
              "सावलीशिवाय. संपूर्ण शेताच्या फोटोपेक्षा एका पानाचा स्पष्ट फोटो "
              "जास्त उपयोगी आहे."},
    "diag.upload": {"en": "Choose a photo", "hi": "फोटो चुनें",
                    "mr": "फोटो निवडा"},
    "diag.camera": {"en": "Take a photo now", "hi": "अभी फोटो लें",
                    "mr": "आत्ता फोटो काढा"},
    "diag.check": {"en": "Check this photo", "hi": "यह फोटो जाँचें",
                   "mr": "हा फोटो तपासा"},
    "diag.working": {"en": "Looking at the photograph…",
                     "hi": "फोटो देखी जा रही है…",
                     "mr": "फोटो पाहिला जात आहे…"},
    "diag.seen": {"en": "What the photo shows", "hi": "फोटो में क्या दिखता है",
                  "mr": "फोटोत काय दिसते"},
    "diag.maybe": {"en": "Possible causes", "hi": "संभावित कारण",
                   "mr": "संभाव्य कारणे"},
    "diag.tells": {"en": "What would confirm it",
                   "hi": "इसकी पुष्टि कैसे होगी",
                   "mr": "याची खात्री कशी होईल"},
    "diag.unsure": {"en": "Not clear enough to name a disease",
                    "hi": "रोग बताने के लिए फोटो पर्याप्त स्पष्ट नहीं",
                    "mr": "रोग सांगण्याइतका फोटो स्पष्ट नाही"},
    "diag.unsure_body": {
        "en": "Several different problems look like this in a photograph. "
              "Rather than guess, take another photo closer to the affected "
              "part, in daylight — or show the plant to your Krishi Sahayak.",
        "hi": "फोटो में कई अलग-अलग समस्याएँ ऐसी ही दिखती हैं। अंदाज़ा लगाने के "
              "बजाय प्रभावित हिस्से के और पास से, दिन के उजाले में दूसरी फोटो "
              "लें — या पौधा अपने कृषि सहायक को दिखाएँ।",
        "mr": "फोटोत अनेक वेगवेगळ्या समस्या अशाच दिसतात. अंदाज लावण्याऐवजी "
              "प्रभावित भागाच्या अधिक जवळून, दिवसाउजेडी दुसरा फोटो काढा — "
              "किंवा झाड तुमच्या कृषी सहायकाला दाखवा."},
    "diag.guidance": {"en": "What the documents say",
                      "hi": "दस्तावेज़ क्या कहते हैं",
                      "mr": "कागदपत्रे काय सांगतात"},
    "diag.verify": {
        "en": "This is a second opinion from a photograph, not a diagnosis. "
              "Confirm with your Krishi Sahayak or KVK before buying or "
              "spraying anything.",
        "hi": "यह फोटो से दी गई दूसरी राय है, निदान नहीं। कुछ भी खरीदने या "
              "छिड़कने से पहले अपने कृषि सहायक या KVK से पुष्टि करें।",
        "mr": "हे फोटोवरून दिलेले दुसरे मत आहे, निदान नाही. काहीही खरेदी "
              "करण्यापूर्वी किंवा फवारण्यापूर्वी तुमच्या कृषी सहायकाची किंवा "
              "KVK ची खात्री करून घ्या."},
    "diag.nophoto": {"en": "Choose or take a photo first",
                     "hi": "पहले फोटो चुनें या लें",
                     "mr": "आधी फोटो निवडा किंवा काढा"},

    # --------------------------------------------------------------- home
    "home.ask": {"en": "Ask a question", "hi": "सवाल पूछें",
                 "mr": "प्रश्न विचारा"},
    "home.today": {"en": "What to do today", "hi": "आज क्या करें",
                   "mr": "आज काय करावे"},
    "home.money": {"en": "Cost & profit", "hi": "लागत और मुनाफ़ा",
                   "mr": "खर्च आणि नफा"},
    "home.market": {"en": "Today's prices", "hi": "आज के भाव",
                    "mr": "आजचे भाव"},
    "home.diagnose": {"en": "Check a sick plant", "hi": "बीमार पौधा जाँचें",
                      "mr": "आजारी झाड तपासा"},
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

    "home.greet": {"en": "Welcome", "hi": "नमस्ते", "mr": "नमस्कार"},

    # ------------------------------------------------- home: hero and chips
    # These lived as English literals inside ui/home.py, which made the
    # language switch look broken: the five nav words changed and the entire
    # rest of the page stayed in English.
    "home.hero": {"en": "The Earthworm is Farming's Best Friend",
                  "hi": "केंचुआ किसान का सबसे अच्छा मित्र है",
                  "mr": "गांडूळ हा शेतकऱ्याचा सर्वोत्तम मित्र"},
    "home.chip_lang": {"en": "Three languages", "hi": "तीन भाषाएँ",
                       "mr": "तीन भाषा"},
    "home.chip_lang_s": {"en": "Marathi · Hindi · English",
                         "hi": "मराठी · हिंदी · अंग्रेज़ी",
                         "mr": "मराठी · हिंदी · इंग्रजी"},
    "home.chip_src": {"en": "Answers with sources", "hi": "स्रोत सहित जवाब",
                      "mr": "स्रोतासह उत्तरे"},
    "home.chip_src_s": {"en": "From real documents", "hi": "असली दस्तावेज़ों से",
                        "mr": "खऱ्या कागदपत्रांतून"},
    "home.chip_voice": {"en": "Speak or listen", "hi": "बोलें या सुनें",
                        "mr": "बोला किंवा ऐका"},
    "home.chip_voice_s": {"en": "No reading needed", "hi": "पढ़ना ज़रूरी नहीं",
                          "mr": "वाचण्याची गरज नाही"},

    # ----------------------------------------------- home: sections
    "home.quick": {"en": "What do you need?", "hi": "आपको क्या चाहिए?",
                   "mr": "तुम्हाला काय हवे आहे?"},
    "home.popular": {"en": "What farmers ask most",
                     "hi": "किसान सबसे ज़्यादा यही पूछते हैं",
                     "mr": "शेतकरी सर्वाधिक हेच विचारतात"},
    "home.farm": {"en": "Your farm", "hi": "आपकी खेती", "mr": "तुमची शेती"},
    "home.farm_place": {"en": "Place", "hi": "जगह", "mr": "ठिकाण"},
    "home.farm_crops": {"en": "Crops", "hi": "फसलें", "mr": "पिके"},
    "home.farm_soil": {"en": "Soil", "hi": "मिट्टी", "mr": "माती"},
    "home.farm_land": {"en": "Land", "hi": "ज़मीन", "mr": "जमीन"},
    "home.acres": {"en": "acres", "hi": "एकड़", "mr": "एकर"},
    "home.farm_empty": {
        "en": "Tell me about your farm in the panel on the left — then the "
              "answers are about your field, not a general one.",
        "hi": "बाईं ओर के पैनल में अपनी खेती बताएं — फिर जवाब आपके खेत के "
              "लिए होंगे, आम नहीं।",
        "mr": "डावीकडील पॅनेलमध्ये तुमच्या शेताची माहिती द्या — मग उत्तरे "
              "तुमच्या शेतासाठी असतील, सर्वसाधारण नाहीत."},

    # ----------------------------------------------- home: why earthworms
    "home.why1": {"en": "Loosens the soil", "hi": "मिट्टी ढीली करता है",
                  "mr": "माती भुसभुशीत करतो"},
    "home.why1d": {
        "en": "Burrowing aerates the soil so roots breathe and grow deeper.",
        "hi": "बिल बनाने से मिट्टी में हवा जाती है, जड़ें साँस लेती हैं और गहरी बढ़ती हैं।",
        "mr": "बिळांमुळे मातीत हवा खेळते, मुळे श्वास घेतात आणि खोलवर वाढतात."},
    "home.why2": {"en": "Improves fertility", "hi": "उर्वरता बढ़ाता है",
                  "mr": "सुपीकता वाढवतो"},
    "home.why2d": {
        "en": "Worm castings are rich in nitrogen, phosphorus and potassium.",
        "hi": "केंचुए की खाद में नाइट्रोजन, फॉस्फोरस और पोटाश भरपूर होता है।",
        "mr": "गांडूळ खतात नत्र, स्फुरद आणि पालाश भरपूर असतात."},
    "home.why3": {"en": "Holds moisture", "hi": "नमी बनाए रखता है",
                  "mr": "ओलावा टिकवतो"},
    "home.why3d": {
        "en": "Burrows help water soak in and stay, reducing irrigation needs.",
        "hi": "बिलों से पानी ज़मीन में उतरता और टिकता है, सिंचाई कम लगती है।",
        "mr": "बिळांमुळे पाणी जमिनीत मुरते आणि टिकते, पाणी कमी लागते."},
    "home.why4": {"en": "Boosts yield", "hi": "पैदावार बढ़ाता है",
                  "mr": "उत्पादन वाढवतो"},
    "home.why4d": {
        "en": "Living soil grows stronger crops and bigger, healthier harvests.",
        "hi": "जीवित मिट्टी में फसल मज़बूत होती है और पैदावार बढ़ती है।",
        "mr": "जिवंत मातीत पीक सशक्त होते आणि उत्पादन वाढते."},

    # ----------------------------------------------- home: friends
    "home.fr1": {"en": "Earthworm", "hi": "केंचुआ", "mr": "गांडूळ"},
    "home.fr1d": {"en": "Tills and enriches the soil from within.",
                  "hi": "मिट्टी को भीतर से जोतता और समृद्ध करता है।",
                  "mr": "माती आतून नांगरतो आणि समृद्ध करतो."},
    "home.fr2": {"en": "Cow", "hi": "गाय", "mr": "गाय"},
    "home.fr2d": {"en": "Dung and urine make natural manure and bio-inputs.",
                  "hi": "गोबर और गोमूत्र से प्राकृतिक खाद और जैविक निवेश बनते हैं।",
                  "mr": "शेण आणि गोमूत्रापासून नैसर्गिक खत आणि जैविक निविष्ठा बनतात."},
    "home.fr3": {"en": "Honey bee", "hi": "मधुमक्खी", "mr": "मधमाशी"},
    "home.fr3d": {"en": "Pollinates crops — more flowers become fruit.",
                  "hi": "परागण करती है — ज़्यादा फूल फल बनते हैं।",
                  "mr": "परागीभवन करते — अधिक फुलांचे फळ होते."},
    "home.fr4": {"en": "Bullock", "hi": "बैल", "mr": "बैल"},
    "home.fr4d": {"en": "Powers ploughing and transport the natural way.",
                  "hi": "जुताई और ढुलाई का प्राकृतिक साधन।",
                  "mr": "नांगरणी आणि वाहतुकीचे नैसर्गिक साधन."},

    # ----------------------------------------------- home: soil bars
    "home.s_n": {"en": "Nitrogen", "hi": "नाइट्रोजन", "mr": "नत्र"},
    "home.s_air": {"en": "Aeration", "hi": "हवा का संचार", "mr": "हवा खेळती राहणे"},
    "home.s_wet": {"en": "Moisture", "hi": "नमी", "mr": "ओलावा"},
    "home.s_yield": {"en": "Crop yield", "hi": "पैदावार", "mr": "उत्पादन"},
    "home.s_org": {"en": "Organic matter", "hi": "जैविक पदार्थ",
                   "mr": "सेंद्रिय पदार्थ"},
    "home.soil_note": {
        "en": "What healthy soil looks like — not a measurement of your field. "
              "For your own land, open Today and tap the soil check.",
        "hi": "यह स्वस्थ मिट्टी का नमूना है, आपके खेत की जाँच नहीं। अपने खेत के "
              "लिए 'आज' खोलें और मिट्टी जाँच दबाएँ।",
        "mr": "हे निरोगी मातीचे उदाहरण आहे, तुमच्या शेताचे मोजमाप नाही. तुमच्या "
              "जमिनीसाठी 'आज' उघडा आणि माती तपासणी दाबा."},

    # ----------------------------------------------- home: ticker, footer
    "home.ticker": {
        "en": "🪱 One earthworm can process its own weight in soil daily "
              "•  🌱 Vermicompost holds 2–3× more nutrients than ordinary soil "
              "•  💧 Earthworm burrows improve water infiltration by up to 10× "
              "•  🌾 Healthy soil biology can raise yields 15–25% "
              "•  🐄 Cow dung + earthworms = the best natural fertiliser",
        "hi": "🪱 एक केंचुआ रोज़ अपने वज़न जितनी मिट्टी पचा सकता है "
              "•  🌱 केंचुआ खाद में साधारण मिट्टी से 2–3 गुना ज़्यादा पोषक तत्व "
              "•  💧 केंचुए के बिल पानी सोखने की क्षमता 10 गुना तक बढ़ाते हैं "
              "•  🌾 स्वस्थ मिट्टी पैदावार 15–25% बढ़ा सकती है "
              "•  🐄 गोबर + केंचुआ = सबसे अच्छी प्राकृतिक खाद",
        "mr": "🪱 एक गांडूळ दररोज स्वतःच्या वजनाएवढी माती पचवू शकतो "
              "•  🌱 गांडूळ खतात सामान्य मातीपेक्षा 2–3 पट अधिक अन्नद्रव्ये "
              "•  💧 गांडुळांच्या बिळांमुळे पाणी मुरण्याचे प्रमाण 10 पटींपर्यंत वाढते "
              "•  🌾 निरोगी माती उत्पादन 15–25% वाढवू शकते "
              "•  🐄 शेण + गांडूळ = सर्वोत्तम नैसर्गिक खत"},
    # ------------------------------------------------- हमीभाव / MSP
    "msp.head": {"en": "Guaranteed price (MSP)",
                 "hi": "न्यूनतम समर्थन मूल्य (MSP)", "mr": "हमीभाव (MSP)"},
    "msp.frp_head": {"en": "Guaranteed price (FRP)",
                     "hi": "उचित एवं लाभकारी मूल्य (FRP)",
                     "mr": "रास्त व किफायतशीर भाव (FRP)"},
    "msp.per": {"en": "per quintal", "hi": "प्रति क्विंटल",
                "mr": "प्रति क्विंटल"},
    "msp.season": {"en": "Season", "hi": "मौसम", "mr": "हंगाम"},
    "msp.above": {"en": "Above the guaranteed price",
                  "hi": "समर्थन मूल्य से ऊपर", "mr": "हमीभावापेक्षा जास्त"},
    "msp.below": {"en": "Below the guaranteed price",
                  "hi": "समर्थन मूल्य से नीचे", "mr": "हमीभावापेक्षा कमी"},
    "msp.below_act": {
        "en": "At this price you would do better at a government procurement "
              "centre, if one is buying your crop this season.",
        "hi": "इस भाव पर सरकारी खरीद केंद्र बेहतर रहेगा, बशर्ते इस मौसम में "
              "आपकी फसल की खरीद हो रही हो।",
        "mr": "या भावाने सरकारी खरेदी केंद्र अधिक फायद्याचे ठरेल, जर या "
              "हंगामात तुमच्या पिकाची खरेदी सुरू असेल तर."},
    "msp.nofloor": {
        "en": "This crop has no guaranteed price. Whatever the market pays is "
              "the price — there is no floor under it.",
        "hi": "इस फसल का कोई समर्थन मूल्य नहीं है। बाज़ार जो दे वही भाव है — "
              "इसके नीचे कोई सीमा नहीं।",
        "mr": "या पिकाला हमीभाव नाही. बाजार जो देईल तोच भाव — त्याखाली कोणतीही "
              "मर्यादा नाही."},
    "msp.frp_note": {
        "en": "Set at 10.25% sugar recovery. Each 0.1 point above adds ₹3.56; "
              "each 0.1 below takes it off. Mills recovering under 9.5% pay a "
              "floor of ₹338.30.",
        "hi": "10.25% चीनी रिकवरी पर तय। हर 0.1 अंक ऊपर पर ₹3.56 अधिक; हर 0.1 "
              "नीचे पर उतना कम। 9.5% से कम रिकवरी वाली मिलें ₹338.30 देती हैं।",
        "mr": "10.25% साखर उताऱ्यावर ठरवलेला. प्रत्येक 0.1 अंक वर ₹3.56 जास्त; "
              "प्रत्येक 0.1 खाली तेवढा कमी. 9.5% पेक्षा कमी उतारा असलेल्या "
              "कारखान्यांना ₹338.30 द्यावा लागतो."},
    "msp.breakeven_under": {
        "en": "Your break-even is below the guaranteed price, so selling at "
              "MSP would cover your costs.",
        "hi": "आपकी लागत समर्थन मूल्य से नीचे है, इसलिए MSP पर बेचने से लागत "
              "निकल आएगी।",
        "mr": "तुमचा उत्पादनखर्च हमीभावापेक्षा कमी आहे, त्यामुळे हमीभावाने "
              "विकल्यास खर्च निघेल."},
    "msp.breakeven_over": {
        "en": "Your break-even is above the guaranteed price. Even selling at "
              "MSP, this crop would lose money at these costs.",
        "hi": "आपकी लागत समर्थन मूल्य से ऊपर है। MSP पर बेचने पर भी इन लागतों "
              "में यह फसल घाटे में रहेगी।",
        "mr": "तुमचा उत्पादनखर्च हमीभावापेक्षा जास्त आहे. हमीभावाने विकले तरी "
              "या खर्चात हे पीक तोट्यात जाईल."},

    # the four Warli panels
    "art.plough": {"en": "Ploughing", "hi": "जुताई", "mr": "नांगरणी"},
    "art.sow": {"en": "Sowing", "hi": "बुवाई", "mr": "पेरणी"},
    "art.rain": {"en": "The rains", "hi": "बारिश", "mr": "पाऊस"},
    "art.harvest": {"en": "Harvest", "hi": "कटाई", "mr": "कापणी"},

    "home.footer": {
        "en": "A farming companion for Marathi, Hindi and English speaking "
              "farmers. Soil first. 🌱",
        "hi": "मराठी, हिंदी और अंग्रेज़ी बोलने वाले किसानों के लिए खेती का साथी। "
              "पहले मिट्टी। 🌱",
        "mr": "मराठी, हिंदी आणि इंग्रजी बोलणाऱ्या शेतकऱ्यांसाठी शेतीचा सोबती. "
              "आधी माती. 🌱"},

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
    "side.setup": {"en": "Setup", "hi": "सेटअप", "mr": "मांडणी"},
    "side.status": {"en": "Status", "hi": "स्थिति", "mr": "स्थिती"},
    "side.local": {"en": "local index", "hi": "लोकल इंडेक्स",
                   "mr": "स्थानिक अनुक्रमणिका"},

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
    # Shown only for the very first question after the app wakes up, while the
    # 2.5 GB embedding model downloads. Without this the generic spinner sits
    # there for a minute or two and people assume it has crashed.
    "common.firstload": {
        "en": "Getting ready — this only happens the first time, "
              "and takes a minute…",
        "hi": "तैयारी हो रही है — यह सिर्फ़ पहली बार होता है, एक मिनट लगेगा…",
        "mr": "तयारी सुरू आहे — हे फक्त पहिल्यांदाच होते, एक मिनिट लागेल…"},
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
