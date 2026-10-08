"""
Turn a village name into coordinates.

Three different features need this — the weather, the spray window and the soil
lookup — and they would otherwise each geocode the same village separately, three
calls for one answer.

So it lives here once, and the answer is written to disk. A village does not
move, so the second lookup and every one after it is free and works offline. That
matters more than it sounds: rural connections drop constantly, and a farmer who
has opened the app once at home should still get their weather in the field.

Open-Meteo's geocoder is free and needs no key. We ask it in English and again
in the local language, because "नाशिक" and "Nashik" are not the same string to a
search index.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import requests

import config

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
CACHE_PATH = config.ROOT / "places_cache.json"
TIMEOUT = 10


@dataclass
class Place:
    name: str            # what we show: "Nashik, Maharashtra, India"
    lat: float
    lon: float
    district: str = ""
    state: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and (self.lat or self.lon)


def _load_cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: dict) -> None:
    try:
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    except Exception:
        pass      # a read-only disk should not stop the app from working


def _ask_openmeteo(query: str, language: str) -> Place | None:
    params = {"name": query, "count": 1, "language": language,
              "countryCode": "IN"}
    response = requests.get(GEOCODE_URL, params=params, timeout=TIMEOUT)
    results = (response.json() or {}).get("results")
    if not results:
        return None

    hit = results[0]
    label = ", ".join(part for part in (hit.get("name"), hit.get("admin1"),
                                        hit.get("country")) if part)
    return Place(
        name=label,
        lat=float(hit["latitude"]),
        lon=float(hit["longitude"]),
        # admin2 is the district in India, admin1 the state
        district=hit.get("admin2") or hit.get("name") or "",
        state=hit.get("admin1") or "",
    )


def find(query: str, lang: str = "en") -> Place:
    """
    Look up a place. Never raises; check `.ok` on the way out.

    Order: the cache, then Open-Meteo in the farmer's language, then in English.
    The second try is worth it because a farmer typing in Marathi and a
    geocoder indexed in English will otherwise simply miss each other.
    """
    query = (query or "").strip()
    if not query:
        return Place("", 0.0, 0.0, error="No place given.")

    cache = _load_cache()
    key = query.lower()
    if key in cache:
        return Place(**cache[key])

    for attempt_lang in dict.fromkeys([lang, "en"]):
        try:
            found = _ask_openmeteo(query, attempt_lang)
        except Exception:
            return Place("", 0.0, 0.0,
                         error=f"Could not look up '{query}' — no internet?")
        if found:
            cache[key] = asdict(found)
            _save_cache(cache)
            return found

    return Place("", 0.0, 0.0, error=f"Place '{query}' not found.")


def forget(query: str) -> None:
    """Drop one place from the cache, for when a lookup went to the wrong town."""
    cache = _load_cache()
    if cache.pop((query or "").strip().lower(), None) is not None:
        _save_cache(cache)
