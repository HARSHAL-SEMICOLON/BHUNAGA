"""
Make the "What should I do today?" briefing.

It gathers everything we know about this farmer's morning -- their profile,
today's weather, the week ahead, whether it is safe to spray, and what the soil
under their feet is like -- and asks the model to turn it into a few things they
can actually go and do.

Two rules shape the code.

Every source is optional. A farmer with no internet still gets the rule-based
alerts, and a farmer whose soil lookup times out still gets the weather. Nothing
in here is allowed to make the briefing fail as a whole.

And the spray window is stated as fact, not left to the model. It is computed
from hourly wind and rain in spray.py, and the exact hours are handed to the
model already worked out. Asking a language model to reason about which hours
are windy is inviting it to invent an answer to a question we can compute.
"""

from __future__ import annotations

import config
from farmer import answer_writer, geo, soil, spray, weather
from farmer.farmer_profile import Profile

LANG_NAME = {"en": "English", "hi": "Hindi", "mr": "Marathi"}


def _resolve_lang(p: Profile) -> str:
    return p.language if p.language in ("en", "hi", "mr") else "en"


def _weather_line(w) -> str:
    if w.error:
        return "weather unavailable"
    return (f"{w.desc}, {w.temp:.0f}C, humidity {w.humidity}%, "
            f"wind {w.wind:.0f} km/h, "
            f"rain over the next 3 days {sum(d['rain'] for d in w.daily[:3]):.0f} mm, "
            f"over 7 days {w.rain_week:.0f} mm")


def _spray_line(advice) -> str:
    """Already-decided fact, not something for the model to work out."""
    if not advice or not advice.ok:
        return ""
    windows = advice.windows(limit=2)
    if not windows:
        return ("SPRAYING: there is no safe hour to spray in the next two days "
                "(wind or rain in every daylight hour). Tell the farmer not to "
                "spray and to check again tomorrow.")
    parts = [f"{s.time.strftime('%A %H:%M')}-{e.time.strftime('%H:%M')}"
             for s, e in windows]
    return ("SPRAYING: the safe hours to spray are " + ", ".join(parts) +
            ". State these hours exactly as given.")


def _soil_line(reading) -> str:
    if not reading or not reading.ok:
        return ""
    bits = [f"{k} {v}" for k, v in reading.values.items()]
    return f"SOIL ({reading.texture or 'texture unknown'}): " + ", ".join(bits)


def build(p: Profile) -> dict:
    """Return everything the briefing card needs. Never raises."""
    location = p.village or p.district or "Pune"
    lang = _resolve_lang(p)

    w = weather.get_weather(location, lang)
    alerts = weather.crop_alerts(w) if not w.error else []

    # one geocode, shared by the spray window and the soil lookup
    place = geo.find(location, lang)
    spray_advice = spray.get_advice(place) if place.ok else None
    soil_reading = soil.get_soil(place) if place.ok else None

    # what the farmer gets if the model is unreachable. it is not a placeholder:
    # the alerts and the spray window are real advice on their own.
    bullets = [f"- {msg}" for _lvl, msg in alerts]
    if spray_advice and spray_advice.ok:
        bullets.insert(0, f"- {spray.summarise(spray_advice)}")
    rule_text = ("Today's farm advice:\n" + "\n".join(bullets)) if bullets else \
        "No major alerts today. Carry on with routine field work."

    facts = [
        f"Farmer: {p.summary() or 'no profile details'}.",
        f"Weather at {location}: {_weather_line(w)}.",
        f"Weather alerts: {'; '.join(m for _l, m in alerts) or 'none'}.",
    ]
    for line in (_spray_line(spray_advice), _soil_line(soil_reading)):
        if line:
            facts.append(line)

    try:
        system = (
            "You are an agricultural advisor for an Indian farmer. Write a "
            "short daily action plan as 3 to 5 bullet points, each something "
            "the farmer can do today or tomorrow.\n"
            "Use ONLY the facts given. Do not invent numbers, and repeat any "
            "spraying hours exactly as they are written.\n"
            "Put the most time-critical point first.\n"
            f"Reply ONLY in {LANG_NAME[lang]}.")
        text = answer_writer.llm_text(system, "\n".join(facts), max_tokens=500)
    except Exception:
        text = rule_text

    return {"weather": w, "alerts": alerts, "text": text, "location": location,
            "spray": spray_advice, "soil": soil_reading, "rule_text": rule_text}
