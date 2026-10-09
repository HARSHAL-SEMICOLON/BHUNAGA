#!/usr/bin/env python3
"""
Check every outside service this app talks to, and say plainly what is wrong.

Run this first whenever something looks broken. It is far quicker than reading
a Streamlit stack trace, and for the mandi price feed it prints the *actual*
field names and filter style that worked, which is the thing that has caused
the most trouble.

    python check_apis.py                 # check everything
    python check_apis.py --place Nashik  # use a different village
    python check_apis.py --raw           # also dump one raw price record
"""

from __future__ import annotations

import argparse
import json
import textwrap

import requests

import config

TICK, CROSS, WARN = "[ ok ]", "[FAIL]", "[warn]"


def head(title: str) -> None:
    print(f"\n{'=' * 62}\n{title}\n{'=' * 62}")


def check_groq() -> None:
    head("Groq — answers and voice")
    if not config.GROQ_API_KEY:
        print(f"{CROSS} GROQ_API_KEY is not set in .env")
        print("       Get a free key at https://console.groq.com/keys")
        return
    print(f"{TICK} key present ({len(config.GROQ_API_KEY)} chars)")
    try:
        from groq import Groq
        reply = Groq(api_key=config.GROQ_API_KEY).chat.completions.create(
            model=config.GROQ_MODEL, max_tokens=256,
            messages=[{"role": "user", "content": "say ok"}])
        said = (reply.choices[0].message.content or "").strip()
        if said:
            print(f"{TICK} {config.GROQ_MODEL} replied: {said!r}")
        else:
            # Reasoning models spend the budget thinking first; an empty reply
            # here means the ceiling was too low, not that the key is bad.
            print(f"{WARN} {config.GROQ_MODEL} replied with empty content -- "
                  "reasoning used the whole budget. Raise GEN_MAX_TOKENS.")
    except Exception as exc:
        print(f"{CROSS} call failed: {str(exc)[:200]}")


def check_vector_store() -> None:
    head("Vector store — where the documents live")
    from farmer import vector_database
    vector_database.reset()
    client = vector_database.get_client()
    backend = vector_database.backend()
    count = vector_database.count(client)

    if backend == "qdrant":
        print(f"{TICK} connected to Qdrant")
    else:
        print(f"{WARN} using the local store on this computer")
        print(f"       Qdrant was not used: {vector_database.why_local()}")
    print(f"       {count} chunks indexed"
          if count >= 0 else "       could not count chunks")
    if count == 0:
        print("       -> nothing is indexed. Either press 'Load sample KB'")
        print("          in the app sidebar, or run:  python ingest.py --recreate")


def check_place(name: str):
    head(f"Open-Meteo geocoding — finding '{name}'")
    from farmer import geo
    geo.forget(name)                       # a cached hit would prove nothing
    place = geo.find(name)
    if not place.ok:
        print(f"{CROSS} {place.error}")
        return None
    print(f"{TICK} {place.name}  ({place.lat:.3f}, {place.lon:.3f})")
    print(f"       district={place.district!r} state={place.state!r}")
    return place


def check_weather(name: str) -> None:
    head("Open-Meteo forecast — weather")
    from farmer import weather
    w = weather.get_weather(name)
    if w.error:
        print(f"{CROSS} {w.error}")
        return
    print(f"{TICK} {w.place}: {w.emoji} {w.desc}, {w.temp:.0f}°C, "
          f"{w.humidity}% humidity, wind {w.wind:.0f} km/h")
    print(f"       {len(w.daily)} day forecast, {w.rain_week:.0f} mm rain expected")
    for level, message in weather.crop_alerts(w)[:3]:
        print(f"       [{level}] {textwrap.shorten(message, 88, placeholder='...')}")


def check_spray(place) -> None:
    head("Open-Meteo hourly — spray window")
    if place is None:
        print(f"{WARN} skipped, no location")
        return
    from farmer import spray
    advice = spray.get_advice(place)
    if not advice.ok:
        print(f"{CROSS} {advice.error}")
        return
    print(f"{TICK} scored {len(advice.hours)} daylight hours, "
          f"{len(advice.best)} are good")
    print(f"       {spray.summarise(advice)}")
    for start, end in advice.windows():
        print(f"       window: {start.label} -> {end.time.strftime('%H:%M')}")


def check_soil(place) -> None:
    head("ISRIC SoilGrids — soil at the farm")
    if place is None:
        print(f"{WARN} skipped, no location")
        return
    from farmer import soil
    result = soil.get_soil(place)
    if not result.ok:
        print(f"{CROSS} {result.error}")
        return
    print(f"{TICK} {result.texture or 'texture unknown'}")
    for label, value in result.values.items():
        print(f"       {label:18} {value}")
    for note in result.notes[:2]:
        print(f"       - {textwrap.shorten(note, 88, placeholder='...')}")


def check_prices(commodity: str, state: str, raw: bool) -> None:
    head(f"data.gov.in — mandi prices for {commodity}")
    from farmer import mandi_prices

    key = config.DATA_GOV_API_KEY or ""
    if key == config.DATA_GOV_DEMO_KEY:
        print(f"{WARN} using the shared demo key — it is heavily rate limited.")
        print("       Get your own free key at https://data.gov.in/help/how-use-datasets-apis")

    mandi_prices.reset_negotiation()
    result = mandi_prices.get_prices(commodity, state)

    if result.source == "live":
        print(f"{TICK} LIVE — {len(result.rows)} rows straight from the API")
    elif result.source == "cached":
        print(f"{WARN} CACHED — the live call failed, showing saved prices")
    else:
        print(f"{CROSS} SAMPLE — live and cache both empty, these are placeholders")
    if result.note:
        print(f"       {result.note}")
    print(f"       what happened: {result.debug}")

    for row in result.rows[:3]:
        print(f"       {row['market']:<16} {row['district']:<12} "
              f"min {row['min']}  max {row['max']}  modal {row['modal']}  "
              f"{row['date']}")

    if raw:
        print("\n       --- one raw record, so we can see the real field names ---")
        try:
            response = requests.get(
                mandi_prices.BASE_URL.format(mandi_prices.PRIMARY_RESOURCE),
                params={"api-key": key, "format": "json", "limit": 1}, timeout=20)
            print(f"       http {response.status_code}")
            records = (response.json() or {}).get("records") or []
            if records:
                print("       " + json.dumps(records[0], indent=8)[:900])
            else:
                print(f"       no records. body: {response.text[:300]}")
        except Exception as exc:
            print(f"       raw fetch failed: {str(exc)[:200]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--place", default="Nashik", help="village or city")
    parser.add_argument("--commodity", default="Onion")
    parser.add_argument("--state", default="Maharashtra")
    parser.add_argument("--raw", action="store_true",
                        help="dump one raw price record")
    args = parser.parse_args()

    print("Checking every outside service Bhunaga uses.")
    print("Anything marked [FAIL] is what to fix first.")

    check_groq()
    check_vector_store()
    place = check_place(args.place)
    check_weather(args.place)
    check_spray(place)
    check_soil(place)
    check_prices(args.commodity, args.state, args.raw)

    print("\nDone.\n")


if __name__ == "__main__":
    main()
