"""
हमीभाव — the government's guaranteed floor price.

What this answers
-----------------
A farmer standing in a mandi with twenty quintals of tur is deciding one
thing: sell here, or take it to a procurement centre. That decision needs the
floor price, and the floor price is not on the trader's board.

Why this is data in the repository rather than an API call
----------------------------------------------------------
MSP is announced once a season by the CCEA on the recommendation of the CACP,
and then it does not move for a year. There is nothing to poll. Shipping it as
a table means this works when the live price feed is down -- which, for
AGMARKNET, is most of the time -- and it costs no model tokens, no network and
no waiting.

Three things it is careful about
--------------------------------
1. Not every crop has one. Onion, tomato, potato and grapes have no MSP at
   all, and a farmer who believes otherwise is counting on a floor that is not
   there. "No MSP for this crop" is a real answer here, not a gap.

2. Sugarcane is not MSP. It has a Fair and Remunerative Price, set per quintal
   against a sugar recovery rate, and it moves with the mill's recovery. It is
   kept separate rather than being flattened into the same table.

3. The season matters. Wheat sown in November is sold in the Rabi marketing
   season of the following year, so the number a farmer needs today is next
   season's, not this one's. Each row says which season it belongs to.

Every figure below is from the government announcement, cited on the row.
Nothing here is estimated, interpolated or carried over from a previous year.
"""

from __future__ import annotations

from dataclasses import dataclass

# ── where these numbers come from ──────────────────────────────────────────
KHARIF_SOURCE = "CCEA, 13 May 2026 (Kharif Marketing Season 2026-27)"
RABI_SOURCE = "Cabinet, 30 September 2026 (Rabi Marketing Season 2027-28)"
FRP_SOURCE = "CCEA, May 2026 (sugar season 2026-27, from 1 October 2026)"

UNIT = "quintal"


@dataclass(frozen=True)
class Support:
    """One guaranteed price, and enough context to trust it."""

    crop: str
    price: int                   # rupees per quintal
    mechanism: str               # "MSP" or "FRP"
    season: str
    source: str
    variety: str = ""            # where a crop has more than one grade
    note: str = ""

    @property
    def label(self) -> str:
        return f"{self.crop} ({self.variety})" if self.variety else self.crop


# ── Kharif 2026-27 ─────────────────────────────────────────────────────────
_KHARIF = [
    ("Paddy", 2441, "common"), ("Paddy", 2461, "Grade A"),
    ("Jowar", 4023, "hybrid"), ("Jowar", 4073, "Maldandi"),
    ("Bajra", 2900, ""), ("Ragi", 5205, ""), ("Maize", 2410, ""),
    ("Tur", 8450, ""), ("Moong", 8780, ""), ("Urad", 8200, ""),
    ("Groundnut", 7517, ""), ("Sunflower", 8343, ""),
    ("Soybean", 5708, "yellow"), ("Sesamum", 10346, ""),
    ("Nigerseed", 10052, ""),
    ("Cotton", 8267, "medium staple"), ("Cotton", 8667, "long staple"),
]

# ── Rabi 2027-28 ───────────────────────────────────────────────────────────
_RABI = [
    ("Wheat", 2610, ""), ("Barley", 2286, ""), ("Gram", 5958, ""),
    ("Lentil", 7390, ""), ("Mustard", 6613, ""), ("Safflower", 7215, ""),
]

TABLE: list[Support] = (
    [Support(c, p, "MSP", "Kharif 2026-27", KHARIF_SOURCE, v) for c, p, v in _KHARIF]
    + [Support(c, p, "MSP", "Rabi 2027-28", RABI_SOURCE, v) for c, p, v in _RABI]
    + [Support("Sugarcane", 365, "FRP", "Sugar season 2026-27", FRP_SOURCE, "",
               "At 10.25% sugar recovery. Each 0.1 point above that adds "
               "₹3.56; each 0.1 below takes it off. Mills recovering "
               "under 9.5% pay a floor of ₹338.30.")]
)

# Crops this app lists that have no guaranteed price at all. Saying so is the
# useful answer -- a farmer who expects a floor under onion and does not get
# one has made the decision on a false premise.
#
# The sentence itself lives in farmer/text.py, not here. An English-only
# explanation would reach exactly the farmers who least need this app.
NO_SUPPORT = {"onion", "tomato", "potato", "grapes"}

# what a farmer, or this app's own crop lists, might call each row
_ALIASES = {
    "paddy": "Paddy", "rice": "Paddy", "bhat": "Paddy", "भात": "Paddy",
    "धान": "Paddy", "तांदूळ": "Paddy",
    "wheat": "Wheat", "gehu": "Wheat", "गहू": "Wheat", "गेहूं": "Wheat",
    "cotton": "Cotton", "kapus": "Cotton", "कापूस": "Cotton", "कपास": "Cotton",
    "soybean": "Soybean", "soyabean": "Soybean", "soya": "Soybean",
    "सोयाबीन": "Soybean",
    "tur": "Tur", "arhar": "Tur", "toor": "Tur", "pigeonpea": "Tur",
    "तूर": "Tur", "अरहर": "Tur",
    "gram": "Gram", "chana": "Gram", "chickpea": "Gram", "हरभरा": "Gram",
    "चना": "Gram",
    "sugarcane": "Sugarcane", "us": "Sugarcane", "ऊस": "Sugarcane",
    "गन्ना": "Sugarcane",
    "jowar": "Jowar", "sorghum": "Jowar", "ज्वारी": "Jowar", "ज्वार": "Jowar",
    "bajra": "Bajra", "pearl millet": "Bajra", "बाजरी": "Bajra",
    "maize": "Maize", "corn": "Maize", "मका": "Maize", "मक्का": "Maize",
    "groundnut": "Groundnut", "peanut": "Groundnut", "भुईमूग": "Groundnut",
    "moong": "Moong", "mung": "Moong", "मूग": "Moong",
    "urad": "Urad", "उडीद": "Urad",
    "ragi": "Ragi", "nachni": "Ragi", "नाचणी": "Ragi",
    "sunflower": "Sunflower", "सूर्यफूल": "Sunflower",
    "mustard": "Mustard", "rapeseed": "Mustard", "मोहरी": "Mustard",
    "sesamum": "Sesamum", "til": "Sesamum", "तीळ": "Sesamum",
    "lentil": "Lentil", "masur": "Lentil", "मसूर": "Lentil",
    "barley": "Barley", "जव": "Barley",
    "safflower": "Safflower", "karadi": "Safflower", "करडई": "Safflower",
    "nigerseed": "Nigerseed", "खुरासणी": "Nigerseed",
}


def canonical(name: str) -> str:
    """Turn whatever the farmer typed into a crop name this table knows."""
    key = (name or "").strip().lower()
    if not key:
        return ""
    if key in _ALIASES:
        return _ALIASES[key]
    # "cotton (long staple)", "soybean seed" and so on
    for alias, crop in _ALIASES.items():
        if alias in key:
            return crop
    return ""


def for_crop(name: str) -> list[Support]:
    """
    Every guaranteed price for this crop, best-known variety first.

    Returns an empty list both for a crop with no support price and for one
    this table has never heard of -- `explain_absence` tells those apart.
    """
    crop = canonical(name)
    if not crop:
        return []
    return [row for row in TABLE if row.crop == crop]


def has_no_floor(name: str) -> bool:
    """
    True when this crop genuinely has no guaranteed price.

    Distinct from "not in the table": an unknown crop means we do not know,
    and onion means there is nothing to know. The screen says different
    things for the two, so the caller has to be able to tell them apart.
    """
    key = (name or "").strip().lower()
    return any(crop in key for crop in NO_SUPPORT)


@dataclass(frozen=True)
class Comparison:
    support: Support
    market_price: float
    gap: float                   # market minus support, rupees per quintal

    @property
    def below(self) -> bool:
        return self.gap < 0

    @property
    def percent(self) -> float:
        if not self.support.price:
            return 0.0
        return self.gap / self.support.price * 100


def compare(market_price: float, support: Support) -> Comparison:
    """How today's price sits against the floor."""
    return Comparison(support, float(market_price),
                      float(market_price) - support.price)


def frp_for_recovery(recovery: float) -> float:
    """
    Sugarcane FRP adjusted for a mill's actual sugar recovery.

    ₹3.56 per quintal for each 0.1 percentage point above 10.25%, and the same
    off for each point below -- except that mills recovering under 9.5% pay a
    floor of ₹338.30 rather than continuing down.
    """
    base, benchmark, step, floor_recovery, floor_price = 365.0, 10.25, 3.56, 9.5, 338.30
    if recovery < floor_recovery:
        return floor_price
    return round(base + ((recovery - benchmark) / 0.1) * step, 2)
