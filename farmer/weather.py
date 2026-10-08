"""
Get the weather and turn it into farming tips.

It uses the free Open-Meteo service (no key needed) to get the temperature,
humidity, rain and wind for a place, plus a 7-day forecast. Then a few simple
rules turn that into advice, like "high humidity -> watch for fungus".
If there is no internet, it returns a friendly message instead of crashing.

A week is the useful length. Three days tells a farmer whether to spray
tomorrow; seven tells them whether to sow this weekend or wait, which is the
decision that actually costs a season if it goes wrong.

Finding the village's coordinates is farmer/geo.py's job, and it caches, so
opening this screen twice does not geocode twice.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import requests

from farmer import geo

FC_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 7

WCODE = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 71: "Snow", 80: "Rain showers", 81: "Rain showers",
    82: "Violent showers", 95: "Thunderstorm", 96: "Thunderstorm w/ hail",
    99: "Thunderstorm w/ heavy hail",
}
WEMOJI = {0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 48: "🌫️",
          51: "🌦️", 53: "🌦️", 55: "🌦️", 61: "🌧️", 63: "🌧️", 65: "🌧️",
          80: "🌦️", 81: "🌧️", 82: "⛈️", 95: "⛈️", 96: "⛈️", 99: "⛈️"}


@dataclass
class Weather:
    place: str
    temp: float
    humidity: int
    precip: float
    wind: float
    code: int
    desc: str
    emoji: str
    daily: list = field(default_factory=list)   # [{date,tmax,tmin,rain,emoji}]
    lat: float = 0.0
    lon: float = 0.0
    error: str = ""

    @property
    def rain_week(self) -> float:
        """Total rain expected over the whole forecast, in mm."""
        return sum(day["rain"] for day in self.daily)


def get_weather(city: str, lang: str = "en") -> Weather:
    try:
        place = geo.find(city, lang)
        if not place.ok:
            return Weather("", 0, 0, 0, 0, 0, "", "", error=place.error)
        lat, lon, label = place.lat, place.lon, place.name
        r = requests.get(FC_URL, params={
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,"
                       "weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,"
                     "precipitation_sum,weather_code",
            "timezone": "auto", "forecast_days": FORECAST_DAYS,
        }, timeout=10).json()
        cur, d = r["current"], r["daily"]
        code = int(cur["weather_code"])
        daily = [{
            "date": d["time"][i], "tmax": d["temperature_2m_max"][i],
            "tmin": d["temperature_2m_min"][i], "rain": d["precipitation_sum"][i],
            "emoji": WEMOJI.get(int(d["weather_code"][i]), "🌡️"),
        } for i in range(len(d["time"]))]
        return Weather(
            place=label, temp=cur["temperature_2m"],
            humidity=int(cur["relative_humidity_2m"]),
            precip=cur["precipitation"], wind=cur["wind_speed_10m"],
            code=code, desc=WCODE.get(code, "—"),
            emoji=WEMOJI.get(code, "🌡️"), daily=daily, lat=lat, lon=lon)
    except Exception as e:  # offline / API down / parse issue
        return Weather("", 0, 0, 0, 0, 0, "", "",
                       error=f"Weather unavailable ({type(e).__name__}).")


def crop_alerts(w: Weather) -> list[tuple[str, str]]:
    """Return [(level, message)] where level in {'warn','info','ok'}."""
    if w.error:
        return []
    out: list[tuple[str, str]] = []
    # near-term rain drives spraying decisions; the week drives sowing ones
    rain_next = sum(day["rain"] for day in w.daily[:3]) if w.daily else 0.0
    rain_week = w.rain_week

    if w.humidity >= 80 and 12 <= w.temp <= 30:
        out.append(("warn",
                    f"High humidity ({w.humidity}%) with mild temperature — "
                    "strong risk of fungal disease (downy/powdery mildew in "
                    "grapes, late blight in tomato/potato). Consider a "
                    "preventive fungicide spray and improve canopy airflow."))
    if rain_next >= 10:
        out.append(("info",
                    f"~{rain_next:.0f} mm rain expected over 3 days — avoid "
                    "spraying and top-dressing fertilizer just before rain; "
                    "ensure field drainage."))
    if w.temp >= 38:
        out.append(("warn",
                    f"High heat ({w.temp:.0f}°C) — irrigate in early morning or "
                    "evening to cut evaporation and heat stress."))
    if w.humidity < 30 and w.temp >= 33:
        out.append(("info",
                    "Hot and dry — high crop water demand; check soil moisture "
                    "and irrigate as needed."))
    if w.wind >= 30:
        out.append(("info",
                    f"Strong wind ({w.wind:.0f} km/h) — postpone spraying to "
                    "avoid drift and provide support to tall crops."))

    # the week-long view: this is the one that decides whether to sow
    if len(w.daily) >= 5:
        if rain_week >= 50:
            out.append(("warn",
                        f"Heavy week ahead — about {rain_week:.0f} mm of rain "
                        "over 7 days. Hold off sowing and clear the field "
                        "drains now, before it starts."))
        elif rain_week >= 15:
            out.append(("ok",
                        f"About {rain_week:.0f} mm of rain expected this week — "
                        "good moisture for sowing once the soil has taken it in."))
        elif rain_week < 2:
            out.append(("info",
                        "Almost no rain expected for a week — plan irrigation, "
                        "and do not sow a rain-fed crop on this forecast."))

    if not out:
        out.append(("ok", "Weather looks favourable — no major crop alerts."))
    return out
