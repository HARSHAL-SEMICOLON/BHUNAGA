"""
When is it safe to spray?

This is the most directly useful thing in the whole app. Spraying in the wrong
conditions is not a small mistake -- the chemical drifts off the field, or the
rain washes it off an hour later, and the farmer has spent real money on
nothing and has to buy and spray again. Every extension service says the same
three things, and almost nobody has the hourly numbers to act on them:

  - wind above about 15 km/h blows the spray off target
  - dead calm (under 3 km/h) is bad too: without a little air movement the
    droplets hang and drift unpredictably later
  - rain within a few hours washes it off before the plant absorbs it
  - above 35 C the droplets evaporate before they land

Open-Meteo gives hourly wind, rain probability, temperature and humidity for
free with no key, so we can score every hour of the next two days and simply
tell the farmer which hours are good.

The thresholds below are the ordinary extension-service ones. They are written
as named constants rather than buried in the code so they can be argued with,
and so a different crop or chemical could use different ones later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import requests

from farmer.geo import Place

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 12

# wind, in km/h
WIND_TOO_STILL = 3.0      # below this, droplets hang in the air
WIND_IDEAL_MAX = 10.0     # the sweet spot ends here
WIND_TOO_STRONG = 15.0    # above this, spray drifts off the field

# rain
RAIN_CHANCE_RISKY = 40    # percent chance within the hour
RAIN_WASHOFF_HOURS = 4    # rain this soon after spraying undoes the work

# temperature, in Celsius
TEMP_TOO_HOT = 35.0       # droplets evaporate before they reach the leaf
HUMIDITY_TOO_LOW = 30     # dry air does the same, more slowly

# only daylight hours are worth suggesting
FIRST_HOUR, LAST_HOUR = 6, 19


@dataclass
class Hour:
    time: datetime
    wind: float
    rain_chance: int
    temp: float
    humidity: int
    score: int = 0               # 0-100, higher is better
    reasons: list = field(default_factory=list)   # why it is not perfect

    @property
    def good(self) -> bool:
        return self.score >= 70

    @property
    def label(self) -> str:
        return self.time.strftime("%a %H:%M")


@dataclass
class SprayAdvice:
    hours: list = field(default_factory=list)     # scored daylight hours
    best: list = field(default_factory=list)      # the good ones, best first
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    @property
    def any_good(self) -> bool:
        return bool(self.best)

    def windows(self, limit: int = 3) -> list[tuple[Hour, Hour]]:
        """
        Group neighbouring good hours into stretches.

        "9:00 to 12:00" is a usable instruction. A list of eleven separate good
        hours is not — nobody reads that and then goes and sprays.
        """
        good = sorted([h for h in self.hours if h.good], key=lambda h: h.time)
        if not good:
            return []

        runs, run = [], [good[0]]
        for hour in good[1:]:
            gap = (hour.time - run[-1].time).total_seconds() / 3600
            if gap <= 1.01:
                run.append(hour)
            else:
                runs.append(run)
                run = [hour]
        runs.append(run)

        runs.sort(key=len, reverse=True)
        return [(r[0], r[-1]) for r in runs[:limit]]


def _score_hour(hour: Hour, rain_soon: bool) -> Hour:
    """Start at perfect and take marks off. Every deduction gets a reason."""
    score = 100

    if hour.wind > WIND_TOO_STRONG:
        score -= 55
        hour.reasons.append(f"wind {hour.wind:.0f} km/h — spray will drift")
    elif hour.wind > WIND_IDEAL_MAX:
        score -= 20
        hour.reasons.append(f"wind {hour.wind:.0f} km/h — a bit breezy")
    elif hour.wind < WIND_TOO_STILL:
        score -= 15
        hour.reasons.append("almost no wind — droplets will hang in the air")

    if hour.rain_chance >= RAIN_CHANCE_RISKY:
        score -= 45
        hour.reasons.append(f"{hour.rain_chance}% chance of rain")
    if rain_soon:
        score -= 35
        hour.reasons.append(f"rain expected within {RAIN_WASHOFF_HOURS} hours — "
                            "it will wash off")

    if hour.temp > TEMP_TOO_HOT:
        score -= 30
        hour.reasons.append(f"{hour.temp:.0f}°C — too hot, it will evaporate")
    if hour.humidity < HUMIDITY_TOO_LOW:
        score -= 10
        hour.reasons.append("very dry air")

    hour.score = max(0, min(100, score))
    return hour


def get_advice(place: Place) -> SprayAdvice:
    """Score the next two days of daylight hours. Never raises."""
    if not place.ok:
        return SprayAdvice(error=place.error or "No location set.")

    try:
        response = requests.get(FORECAST_URL, params={
            "latitude": place.lat, "longitude": place.lon,
            "hourly": "temperature_2m,relative_humidity_2m,"
                      "precipitation_probability,wind_speed_10m",
            "timezone": "auto", "forecast_days": 2,
        }, timeout=TIMEOUT)
        data = response.json()["hourly"]
    except Exception as exc:
        return SprayAdvice(error=f"Spray forecast unavailable "
                                 f"({type(exc).__name__}).")

    times = data["time"]
    rain_chances = data["precipitation_probability"]

    hours = []
    for i, stamp in enumerate(times):
        when = datetime.fromisoformat(stamp)
        if not FIRST_HOUR <= when.hour <= LAST_HOUR:
            continue

        # look ahead: spraying now is wasted if it rains in a few hours
        ahead = rain_chances[i + 1:i + 1 + RAIN_WASHOFF_HOURS]
        rain_soon = any((c or 0) >= RAIN_CHANCE_RISKY for c in ahead)

        hours.append(_score_hour(Hour(
            time=when,
            wind=float(data["wind_speed_10m"][i] or 0),
            rain_chance=int(rain_chances[i] or 0),
            temp=float(data["temperature_2m"][i] or 0),
            humidity=int(data["relative_humidity_2m"][i] or 0),
        ), rain_soon))

    best = sorted([h for h in hours if h.good],
                  key=lambda h: (-h.score, h.time))
    return SprayAdvice(hours=hours, best=best)


def summarise(advice: SprayAdvice) -> str:
    """One line a farmer can act on without reading a table."""
    if not advice.ok:
        return advice.error
    windows = advice.windows()
    if not windows:
        return ("No good spraying hours in the next two days — wind or rain "
                "every daylight hour. Wait and check again tomorrow.")
    start, end = windows[0]
    when = start.time.strftime("%A")
    return (f"Best time to spray: {when} "
            f"{start.time.strftime('%H:%M')}–{end.time.strftime('%H:%M')}.")
