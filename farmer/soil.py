"""
What the soil is like at the farmer's own coordinates.

ISRIC SoilGrids is a global soil map built from machine learning over a large
pile of real soil surveys. It is free, needs no key, and answers for any point
on land. We ask for the topsoil layer (0-30 cm), which is the part a plough
turns and a root lives in.

Be honest about what this is. SoilGrids is a *model prediction* at roughly 250 m
resolution, not a test of this particular field. It is genuinely useful for
"my soil is clayey and slightly alkaline, so which crop suits it" and genuinely
not a substitute for a Soil Health Card. The app says so on screen, because a
farmer who fertilises against a wrong number pays for it.

The numbers come back in odd units -- SoilGrids stores them as integers to save
space, so pH arrives as 72 meaning 7.2, and clay as 340 meaning 34.0%. The
conversion factors are published per property and are applied below.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import requests

from farmer.geo import Place

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
TIMEOUT = 25          # this service is thorough rather than fast
DEPTH = "0-30cm"      # the plough layer
STAT = "mean"

# property -> (what we call it, divide the stored integer by this, unit)
WANTED = {
    "phh2o": ("pH", 10.0, ""),
    "soc": ("Organic carbon", 10.0, "g/kg"),
    "clay": ("Clay", 10.0, "%"),
    "sand": ("Sand", 10.0, "%"),
    "silt": ("Silt", 10.0, "%"),
    "nitrogen": ("Nitrogen", 100.0, "g/kg"),
    "cec": ("Nutrient holding", 10.0, "cmol/kg"),
}


@dataclass
class Soil:
    place: str = ""
    values: dict = field(default_factory=dict)   # {"pH": 7.2, "Clay": 34.0, ...}
    texture: str = ""                            # "Clay loam", "Sandy loam", ...
    notes: list = field(default_factory=list)    # plain advice, one per line
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.values)


def classify(clay: float, sand: float, silt: float) -> str:
    """
    Name the texture from the three fractions.

    A simplified reading of the USDA soil texture triangle — enough to tell a
    farmer whether their soil drains fast or holds water, which is the part
    that changes what they should do.
    """
    if clay >= 40:
        return "Clay"
    if clay >= 27:
        return "Clay loam" if sand < 45 else "Sandy clay loam"
    if sand >= 70:
        return "Loamy sand" if clay >= 7 else "Sand"
    if sand >= 52:
        return "Sandy loam"
    if silt >= 50:
        return "Silt loam" if clay < 27 else "Silty clay loam"
    return "Loam"


def _advise(values: dict, texture: str) -> list[str]:
    """Turn the numbers into things a farmer can actually do."""
    notes = []

    ph = values.get("pH")
    if ph is not None:
        if ph < 5.5:
            notes.append(f"Acidic soil (pH {ph:.1f}). Lime raises pH; without it "
                         "phosphorus stays locked up and the crop cannot reach it.")
        elif ph > 8.5:
            notes.append(f"Alkaline soil (pH {ph:.1f}). Gypsum and plenty of "
                         "organic matter help. Iron and zinc will be short — "
                         "watch for yellowing between the leaf veins.")
        else:
            notes.append(f"pH {ph:.1f} — in the comfortable range for most crops.")

    carbon = values.get("Organic carbon")
    if carbon is not None:
        if carbon < 5:
            notes.append(f"Low organic carbon ({carbon:.1f} g/kg). This is the "
                         "single best thing to fix: compost, vermicompost, green "
                         "manure or crop residue. Everything else works better "
                         "once it is up.")
        elif carbon > 15:
            notes.append(f"Good organic carbon ({carbon:.1f} g/kg) — the soil is "
                         "biologically alive. Keep returning residue to it.")

    if texture in ("Sand", "Loamy sand", "Sandy loam"):
        notes.append("Light, free-draining soil. Water and nutrients both leach "
                     "away, so irrigate little and often and split the fertiliser "
                     "into several doses instead of one.")
    elif texture in ("Clay", "Clay loam", "Silty clay loam"):
        notes.append("Heavy soil that holds water. Make sure it drains after "
                     "heavy rain, and do not work it while it is wet or it will "
                     "set hard.")

    cec = values.get("Nutrient holding")
    if cec is not None and cec < 10:
        notes.append("The soil holds nutrients poorly, so applied fertiliser "
                     "washes out easily. Organic matter is what fixes this.")

    return notes


def _read(layers: list) -> dict:
    """Pull the values we asked for out of the SoilGrids response."""
    values = {}
    for layer in layers:
        spec = WANTED.get(layer.get("name"))
        if not spec:
            continue
        label, divisor, _unit = spec
        for depth in layer.get("depths", []):
            if depth.get("label") != DEPTH:
                continue
            raw = (depth.get("values") or {}).get(STAT)
            if raw is not None:
                values[label] = round(float(raw) / divisor, 2)
    return values


def get_soil(place: Place) -> Soil:
    """Look up the soil at a place. Never raises."""
    if not place.ok:
        return Soil(error=place.error or "No location set.")

    params = [("lon", place.lon), ("lat", place.lat),
              ("depth", DEPTH), ("value", STAT)]
    params += [("property", name) for name in WANTED]

    try:
        response = requests.get(SOILGRIDS_URL, params=params, timeout=TIMEOUT)
        if response.status_code != 200:
            return Soil(error=f"Soil service returned {response.status_code}. "
                              f"Try again in a minute.")
        layers = response.json()["properties"]["layers"]
    except Exception as exc:
        return Soil(error=f"Soil data unavailable ({type(exc).__name__}).")

    values = _read(layers)
    if not values:
        return Soil(error="No soil data for this location — SoilGrids covers "
                          "land, so check the village name is right.")

    texture = ""
    if all(k in values for k in ("Clay", "Sand", "Silt")):
        texture = classify(values["Clay"], values["Sand"], values["Silt"])

    return Soil(place=place.name, values=values, texture=texture,
                notes=_advise(values, texture))


# what the app shows underneath the numbers, so nobody mistakes this for a test
DISCLAIMER = ("These are modelled estimates from a global soil map (ISRIC "
              "SoilGrids), not a test of your field. Use them to understand "
              "your soil, not to decide exact fertiliser amounts — for that, "
              "get a Soil Health Card.")
