"""
Mandi (market) prices from the government's Agmarknet feed on data.gov.in.

Why this file is more complicated than it looks
-----------------------------------------------
data.gov.in has changed its API surface more than once. Depending on which
version of the resource you hit, the same dataset wants

    filters[state]=Maharashtra
    filters[State]=Maharashtra
    filters[State.keyword]=Maharashtra

and returns its columns as either `min_price` or `Min_Price`. Guessing wrong
does not produce an error -- it returns HTTP 200 with zero records, which is
exactly how this app ended up quietly showing sample prices while looking like
it was working.

So we do not guess. We try each filter style in turn until one returns rows,
remember which one worked, and read every field through a list of aliases so the
capitalisation does not matter. If every filtered style fails we fetch unfiltered
and filter in Python, which always works as long as the feed is up at all.

The ladder, in order:
    1. live API, negotiating the filter style
    2. a second government resource, if the first has nothing for this commodity
    3. the cache on disk, with its age shown
    4. bundled sample prices, clearly labelled as not real

Every result says which rung it came from, because a farmer deciding when to
sell needs to know whether the number is today's or a placeholder.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import requests

import config

# "Current daily price of various commodities from various markets (Mandi)"
PRIMARY_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"
# A second Agmarknet-derived resource, used when the first has nothing.
BACKUP_RESOURCE = "35985678-0d79-46b4-9ed6-6f13308a1d24"
RESOURCES = (PRIMARY_RESOURCE, BACKUP_RESOURCE)

BASE_URL = "https://api.data.gov.in/resource/{}"
CACHE_PATH = config.ROOT / "market_cache.json"
CACHE_FRESH_HOURS = 18        # older than this and we say so on screen
TIMEOUT = 20
# Consecutive network-level failures before abandoning the ladder. The
# filter-spelling search is worth paying for once; it is not worth paying
# a 20-second timeout six times over to rediscover that the host is down.
NETWORK_FAILURES_BEFORE_GIVING_UP = 2

# The filter spellings the API has used, newest first. Whichever returns rows
# wins and is remembered for the rest of the session.
FILTER_STYLES = ("{}.keyword", "{}")
FIELD_CASES = (
    {"state": "State", "district": "District", "commodity": "Commodity"},
    {"state": "state", "district": "district", "commodity": "commodity"},
)

# Every spelling a column has appeared under. First one present wins.
ALIASES = {
    "market": ("market", "Market", "market_name"),
    "commodity": ("commodity", "Commodity", "commodity_name"),
    "variety": ("variety", "Variety"),
    "district": ("district", "District", "district_name"),
    "state": ("state", "State", "state_name"),
    "min": ("min_price", "Min_Price", "minprice", "Min Price"),
    "max": ("max_price", "Max_Price", "maxprice", "Max Price"),
    "modal": ("modal_price", "Modal_Price", "modalprice", "Modal Price"),
    "date": ("arrival_date", "Arrival_Date", "arrivaldate", "Arrival Date"),
}

SAMPLE = {
    "Onion":     [("Lasalgaon", "Nashik", 1200, 1800, 1500),
                  ("Pune", "Pune", 1300, 2000, 1650)],
    "Tomato":    [("Narayangaon", "Pune", 800, 1600, 1200),
                  ("Nashik", "Nashik", 700, 1500, 1100)],
    "Potato":    [("Pune", "Pune", 1000, 1500, 1250)],
    "Cotton":    [("Akola", "Akola", 6800, 7400, 7100)],
    "Soybean":   [("Latur", "Latur", 4200, 4800, 4500)],
    "Wheat":     [("Pune", "Pune", 2200, 2600, 2400)],
    "Grapes":    [("Nashik", "Nashik", 4000, 7000, 5500)],
    "Sugarcane": [("Kolhapur", "Kolhapur", 280, 320, 300)],
    "Tur":       [("Latur", "Latur", 9000, 11000, 10000)],
    "Gram":      [("Latur", "Latur", 4800, 5600, 5200)],
}

# the style that worked, remembered so we only pay the search cost once
_working_style: tuple | None = None


@dataclass
class MarketResult:
    rows: list = field(default_factory=list)
    source: str = "live"          # live | cached | sample
    note: str = ""
    error: str = ""
    debug: str = ""

    @property
    def is_real(self) -> bool:
        """True when these are actual reported prices, not placeholders."""
        return self.source in ("live", "cached") and bool(self.rows)


def _pick(record: dict, field_name: str):
    """Read one column whatever the feed decided to call it today."""
    for alias in ALIASES[field_name]:
        if alias in record and record[alias] not in (None, ""):
            return record[alias]
    # last resort: match ignoring case and punctuation
    flat = {k.lower().replace(" ", "_"): v for k, v in record.items()}
    for alias in ALIASES[field_name]:
        value = flat.get(alias.lower().replace(" ", "_"))
        if value not in (None, ""):
            return value
    return ""


def _rows_from_records(records) -> list[dict]:
    rows = []
    for record in records:
        rows.append({
            "market": _pick(record, "market"),
            "commodity": _pick(record, "commodity"),
            "variety": _pick(record, "variety"),
            "district": _pick(record, "district"),
            "min": _pick(record, "min"),
            "max": _pick(record, "max"),
            "modal": _pick(record, "modal"),
            "date": _pick(record, "date"),
        })
    return rows


def _matches(row: dict, commodity: str, state: str, district: str) -> bool:
    """
    Client-side filtering, for when every server-side filter style failed.

    State is deliberately not checked: the backup resource does not always
    carry a state column, and dropping every row for a missing field would turn
    a working fallback into an empty screen. District is specific enough.
    """
    def same(value, wanted):
        return not wanted or wanted.strip().lower() in str(value).strip().lower()

    return same(row["commodity"], commodity) and same(row["district"], district)


def _build_params(style: str, cases: dict, commodity: str, state: str,
                  district: str, limit: int) -> dict:
    params = {"api-key": config.DATA_GOV_API_KEY, "format": "json",
              "limit": limit}
    params[f"filters[{style.format(cases['commodity'])}]"] = commodity
    if state:
        params[f"filters[{style.format(cases['state'])}]"] = state
    if district:
        params[f"filters[{style.format(cases['district'])}]"] = district
    return params


def _attempts(commodity: str, state: str, district: str, limit: int):
    """
    Every (resource, params, label) worth trying, best first.

    A style that has already worked this session is tried first, so the search
    cost is paid once rather than on every lookup.
    """
    combos = [(style, cases) for style in FILTER_STYLES for cases in FIELD_CASES]
    if _working_style and _working_style in combos:
        combos.remove(_working_style)
        combos.insert(0, _working_style)

    for resource in RESOURCES:
        for style, cases in combos:
            yield (resource, (style, cases),
                   _build_params(style, cases, commodity, state, district, limit),
                   f"{resource[:8]} filters[{style.format(cases['commodity'])}]")
        # nothing filtered worked: take a big unfiltered page and sort it here
        yield (resource, None,
               {"api-key": config.DATA_GOV_API_KEY, "format": "json",
                "limit": max(limit, 1000)},
               f"{resource[:8]} unfiltered")


def _fetch_live(commodity: str, state: str, district: str, limit: int):
    """Walk the ladder. Returns (rows, debug) with rows empty if nothing worked."""
    global _working_style
    notes = []
    unreachable = 0

    for resource, combo, params, label in _attempts(commodity, state, district,
                                                    limit):
        # Two different failures look alike in the notes but mean opposite
        # things. "HTTP 200 with zero rows" is the one this ladder exists for:
        # the filter spelling was wrong, so try the next. A timeout or a
        # refused connection means the host is not answering at all, and no
        # spelling fixes that -- walking the remaining attempts just pays the
        # timeout again. Six attempts at TIMEOUT=20 is two minutes of a frozen
        # spinner before the farmer is shown sample prices anyway.
        if unreachable >= NETWORK_FAILURES_BEFORE_GIVING_UP:
            notes.append("gave up: data.gov.in is not responding")
            break
        try:
            response = requests.get(BASE_URL.format(resource), params=params,
                                    timeout=TIMEOUT)
        except requests.exceptions.Timeout:
            unreachable += 1
            notes.append(f"{label}: timeout")
            continue
        except requests.exceptions.ConnectionError:
            unreachable += 1
            notes.append(f"{label}: unreachable")
            continue
        except Exception as exc:
            notes.append(f"{label}: {type(exc).__name__}")
            continue

        unreachable = 0      # the host answered; later failures are about data

        if response.status_code != 200:
            notes.append(f"{label}: http {response.status_code}")
            continue

        try:
            records = (response.json() or {}).get("records") or []
        except ValueError:
            notes.append(f"{label}: not json")
            continue

        if not records:
            notes.append(f"{label}: 0 rows")
            continue

        rows = _rows_from_records(records)
        if combo is None:
            # unfiltered page: keep only what the farmer asked about
            rows = [r for r in rows if _matches(r, commodity, state, district)]
            if not rows:
                notes.append(f"{label}: no match in {len(records)} rows")
                continue
        else:
            _working_style = combo

        return rows[:limit], f"{label}: {len(rows)} rows"

    return [], " | ".join(notes[-6:])


# the cache on disk
def _load_cache(commodity: str):
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8")).get(commodity)
    except Exception:
        return None


def _save_cache(commodity: str, rows: list) -> None:
    try:
        data = {}
        if CACHE_PATH.exists():
            data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        data[commodity] = {"rows": rows, "saved": time.strftime("%Y-%m-%d %H:%M"),
                           "epoch": time.time()}
        CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False),
                              encoding="utf-8")
    except Exception:
        pass


def _cache_age_hours(entry: dict) -> float:
    epoch = entry.get("epoch")
    if not epoch:
        return 999.0
    return (time.time() - float(epoch)) / 3600


def _sample(commodity: str) -> list[dict]:
    return [{"market": m, "commodity": commodity, "variety": "", "district": d,
             "min": mn, "max": mx, "modal": md, "date": "sample"}
            for (m, d, mn, mx, md) in SAMPLE.get(commodity, [])]


def get_prices(commodity: str, state: str = "Maharashtra", district: str = "",
               limit: int = 50) -> MarketResult:
    """Today's prices if we can get them, and an honest label if we cannot."""
    key = config.DATA_GOV_API_KEY or ""
    debug = f"key_len={len(key)}"

    rows, live_debug = _fetch_live(commodity, state, district, limit)
    debug = f"{debug} {live_debug}"

    if rows:
        _save_cache(commodity, rows)
        return MarketResult(rows=rows, source="live", debug=debug)

    cached = _load_cache(commodity)
    if cached and cached.get("rows"):
        age = _cache_age_hours(cached)
        stale = age > CACHE_FRESH_HOURS
        when = cached.get("saved", "earlier")
        return MarketResult(
            rows=cached["rows"], source="cached",
            note=(f"Live prices unavailable — showing prices saved {when}"
                  + (f", about {age:.0f} hours old. Treat them as a guide, "
                     "not today's rate." if stale else ".")),
            debug=debug)

    rows = _sample(commodity)
    if rows:
        return MarketResult(
            rows=rows, source="sample",
            note="Live prices unavailable and nothing saved yet — these are "
                 "example figures to show how the screen works. They are NOT "
                 "today's rates; check your mandi board before selling.",
            debug=debug)

    return MarketResult(error=f"No prices available for {commodity}.",
                        debug=debug)


def reset_negotiation() -> None:
    """Forget the remembered filter style, so the next call searches again."""
    global _working_style
    _working_style = None
