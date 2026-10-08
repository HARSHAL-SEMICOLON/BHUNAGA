"""
Tests for the outside services: prices, weather, spraying, soil, geocoding.

Not one of these touches the network. Every response is a canned dictionary,
which lets us test the cases that actually break in the field and are impossible
to trigger on demand -- a 200 with zero records, a renamed column, a timeout, a
cluster that answers 404.

The price tests are the important ones. The bug that made this app quietly show
sample prices was not a crash: data.gov.in returned HTTP 200 and an empty list
because the filter was spelled the way an older version of the API wanted. So
the tests below feed the client each plausible API shape and check it finds the
data anyway.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from farmer import geo, mandi_prices, soil, spray, weather


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = str(payload)[:200]

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


# --------------------------------------------------------------- price rows
NEW_STYLE = {"State": "Maharashtra", "District": "Nashik", "Market": "Lasalgaon",
             "Commodity": "Onion", "Variety": "Red", "Arrival_Date": "15/08/2026",
             "Min_Price": "1200", "Max_Price": "1800", "Modal_Price": "1500"}
OLD_STYLE = {"state": "Maharashtra", "district": "Nashik", "market": "Lasalgaon",
             "commodity": "Onion", "variety": "Red", "arrival_date": "15/08/2026",
             "min_price": "1200", "max_price": "1800", "modal_price": "1500"}
SPACED_STYLE = {"State": "Maharashtra", "District": "Nashik",
                "Market": "Lasalgaon", "Commodity": "Onion", "Variety": "Red",
                "Arrival Date": "15/08/2026", "Min Price": "1200",
                "Max Price": "1800", "Modal Price": "1500"}


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    """Each test starts with no cache and no remembered filter style."""
    monkeypatch.setattr(mandi_prices, "CACHE_PATH", tmp_path / "market.json")
    mandi_prices.reset_negotiation()
    yield
    mandi_prices.reset_negotiation()


@pytest.mark.parametrize("record", [NEW_STYLE, OLD_STYLE, SPACED_STYLE])
def test_columns_are_read_whatever_they_are_called(record):
    """Capitalisation has changed at least twice. It must not matter."""
    rows = mandi_prices._rows_from_records([record])
    assert rows[0]["market"] == "Lasalgaon"
    assert rows[0]["district"] == "Nashik"
    assert rows[0]["min"] == "1200"
    assert rows[0]["max"] == "1800"
    assert rows[0]["modal"] == "1500"
    assert rows[0]["date"] == "15/08/2026"


def test_a_completely_unknown_column_set_does_not_crash():
    rows = mandi_prices._rows_from_records([{"totally": "different"}])
    assert rows[0]["market"] == "" and rows[0]["modal"] == ""


@pytest.mark.parametrize("wanted_filter", [
    "filters[Commodity.keyword]", "filters[Commodity]",
    "filters[commodity.keyword]", "filters[commodity]",
])
def test_client_finds_whichever_filter_spelling_works(monkeypatch, wanted_filter):
    """
    The heart of the fix.

    Only one spelling returns rows; every other one returns 200 with an empty
    list, exactly like the real API does. The client has to keep going until it
    finds the one that works instead of believing the first empty answer.
    """
    seen = []

    def fake_get(url, params=None, timeout=None):
        seen.append(params)
        if wanted_filter in params:
            return FakeResponse({"records": [NEW_STYLE]})
        return FakeResponse({"records": []})

    monkeypatch.setattr(mandi_prices.requests, "get", fake_get)
    result = mandi_prices.get_prices("Onion")
    assert result.source == "live", result.debug
    assert result.rows[0]["modal"] == "1500"
    # whichever spelling it was, the call that succeeded is the last one tried
    assert wanted_filter in seen[-1]


def test_an_empty_200_does_not_stop_the_search(monkeypatch):
    """
    The specific bug this replaced.

    data.gov.in answers a wrong filter spelling with HTTP 200 and an empty list,
    not an error. Believing that first empty answer is what left the app quietly
    showing sample prices while looking like it worked.
    """
    seen = []

    def fake_get(url, params=None, timeout=None):
        seen.append(params)
        # only the *last* spelling in the ladder has the data
        if "filters[commodity]" in params:
            return FakeResponse({"records": [OLD_STYLE]})
        return FakeResponse({"records": []})

    monkeypatch.setattr(mandi_prices.requests, "get", fake_get)
    result = mandi_prices.get_prices("Onion")
    assert result.source == "live", result.debug
    assert len(seen) > 1, "should have kept trying past the empty 200"


def test_a_working_style_is_remembered(monkeypatch):
    """Having found the right spelling, we should not search again every time."""
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        if "filters[Commodity]" in params:
            return FakeResponse({"records": [NEW_STYLE]})
        return FakeResponse({"records": []})

    monkeypatch.setattr(mandi_prices.requests, "get", fake_get)
    mandi_prices.get_prices("Onion")
    first_round = len(calls)
    calls.clear()
    mandi_prices.get_prices("Onion")
    assert len(calls) < first_round, "the second call should be shorter"


def test_falls_back_to_unfiltered_and_filters_here(monkeypatch):
    """
    When no filter spelling works at all, take a big page and sort it ourselves.
    This always works as long as the feed is up.
    """
    other = dict(NEW_STYLE, Commodity="Wheat", Market="Pune")

    def fake_get(url, params=None, timeout=None):
        if any(k.startswith("filters[") for k in params):
            return FakeResponse({"records": []})
        return FakeResponse({"records": [other, NEW_STYLE]})

    monkeypatch.setattr(mandi_prices.requests, "get", fake_get)
    result = mandi_prices.get_prices("Onion")
    assert result.source == "live"
    assert len(result.rows) == 1
    assert result.rows[0]["commodity"] == "Onion", "wheat should be filtered out"


def test_http_500_falls_through_to_sample(monkeypatch):
    monkeypatch.setattr(mandi_prices.requests, "get",
                        lambda *a, **k: FakeResponse({}, status=500))
    result = mandi_prices.get_prices("Onion")
    assert result.source == "sample"
    assert "500" in result.debug


def test_timeout_falls_through_to_sample(monkeypatch):
    def boom(*a, **k):
        raise mandi_prices.requests.exceptions.Timeout()
    monkeypatch.setattr(mandi_prices.requests, "get", boom)
    result = mandi_prices.get_prices("Onion")
    assert result.source == "sample" and "timeout" in result.debug


def test_a_live_result_is_cached_and_then_served_when_live_fails(monkeypatch):
    monkeypatch.setattr(mandi_prices.requests, "get",
                        lambda *a, **k: FakeResponse({"records": [NEW_STYLE]}))
    first = mandi_prices.get_prices("Onion")
    assert first.source == "live"

    # now the API goes down
    def boom(*a, **k):
        raise ConnectionError("network gone")
    monkeypatch.setattr(mandi_prices.requests, "get", boom)
    mandi_prices.reset_negotiation()
    second = mandi_prices.get_prices("Onion")
    assert second.source == "cached"
    assert second.rows[0]["modal"] == "1500"
    assert second.note


def test_sample_prices_say_loudly_that_they_are_not_real(monkeypatch):
    """A farmer selling against a placeholder number loses real money."""
    monkeypatch.setattr(mandi_prices.requests, "get",
                        lambda *a, **k: FakeResponse({"records": []}))
    result = mandi_prices.get_prices("Onion")
    assert result.source == "sample"
    assert "NOT" in result.note
    assert result.is_real is False


def test_live_and_cached_are_flagged_as_real(monkeypatch):
    monkeypatch.setattr(mandi_prices.requests, "get",
                        lambda *a, **k: FakeResponse({"records": [NEW_STYLE]}))
    assert mandi_prices.get_prices("Onion").is_real is True


def test_unknown_commodity_with_no_sample_returns_an_error(monkeypatch):
    monkeypatch.setattr(mandi_prices.requests, "get",
                        lambda *a, **k: FakeResponse({"records": []}))
    result = mandi_prices.get_prices("Dragonfruit")
    assert result.error and not result.rows


# ------------------------------------------------------------- spray window
def _hourly(hours=24, wind=6.0, rain=0, temp=28.0, humidity=55):
    start = datetime(2026, 8, 16, 0, 0)
    times = [(start + timedelta(hours=i)).isoformat() for i in range(hours)]
    return {"hourly": {
        "time": times,
        "wind_speed_10m": [wind] * hours,
        "precipitation_probability": [rain] * hours,
        "temperature_2m": [temp] * hours,
        "relative_humidity_2m": [humidity] * hours,
    }}


PLACE = geo.Place(name="Nashik", lat=20.0, lon=73.8)


def test_calm_clear_weather_gives_good_hours(monkeypatch):
    monkeypatch.setattr(spray.requests, "get",
                        lambda *a, **k: FakeResponse(_hourly()))
    advice = spray.get_advice(PLACE)
    assert advice.ok and advice.any_good
    # only daylight hours are offered; nobody sprays at 3am
    assert all(spray.FIRST_HOUR <= h.time.hour <= spray.LAST_HOUR
               for h in advice.hours)


def test_strong_wind_rules_every_hour_out(monkeypatch):
    monkeypatch.setattr(spray.requests, "get",
                        lambda *a, **k: FakeResponse(_hourly(wind=25.0)))
    advice = spray.get_advice(PLACE)
    assert not advice.any_good
    assert any("drift" in r for h in advice.hours for r in h.reasons)


def test_rain_rules_every_hour_out(monkeypatch):
    monkeypatch.setattr(spray.requests, "get",
                        lambda *a, **k: FakeResponse(_hourly(rain=90)))
    advice = spray.get_advice(PLACE)
    assert not advice.any_good
    assert any("rain" in r for h in advice.hours for r in h.reasons)


def test_dead_calm_is_penalised_too(monkeypatch):
    """Not obvious, but real: with no air movement droplets hang and drift."""
    monkeypatch.setattr(spray.requests, "get",
                        lambda *a, **k: FakeResponse(_hourly(wind=0.5)))
    advice = spray.get_advice(PLACE)
    assert any("hang" in r for h in advice.hours for r in h.reasons)


def test_extreme_heat_is_penalised(monkeypatch):
    monkeypatch.setattr(spray.requests, "get",
                        lambda *a, **k: FakeResponse(_hourly(temp=42.0)))
    advice = spray.get_advice(PLACE)
    assert any("evaporate" in r for h in advice.hours for r in h.reasons)


def test_good_hours_are_grouped_into_windows(monkeypatch):
    """Eleven separate good hours is not an instruction anyone can act on."""
    monkeypatch.setattr(spray.requests, "get",
                        lambda *a, **k: FakeResponse(_hourly()))
    advice = spray.get_advice(PLACE)
    windows = advice.windows()
    assert windows
    start, end = windows[0]
    assert end.time > start.time


def test_summary_is_one_actionable_line(monkeypatch):
    monkeypatch.setattr(spray.requests, "get",
                        lambda *a, **k: FakeResponse(_hourly()))
    line = spray.summarise(spray.get_advice(PLACE))
    assert "Best time to spray" in line and "–" in line


def test_spray_without_a_location_explains_itself():
    advice = spray.get_advice(geo.Place("", 0.0, 0.0, error="Place not found."))
    assert not advice.ok and "not found" in advice.error


def test_spray_api_failure_is_caught(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError()
    monkeypatch.setattr(spray.requests, "get", boom)
    assert not spray.get_advice(PLACE).ok


# --------------------------------------------------------------------- soil
def _soil_payload():
    def layer(name, value):
        return {"name": name, "depths": [{"label": "0-30cm",
                                          "values": {"mean": value}}]}
    return {"properties": {"layers": [
        layer("phh2o", 72),        # stored as 72, means pH 7.2
        layer("soc", 45),          # 4.5 g/kg
        layer("clay", 340),        # 34.0 %
        layer("sand", 300),
        layer("silt", 360),
        layer("cec", 180),
    ]}}


def test_soilgrids_integers_are_converted(monkeypatch):
    """SoilGrids stores pH 7.2 as the integer 72. Getting this wrong is silent."""
    monkeypatch.setattr(soil.requests, "get",
                        lambda *a, **k: FakeResponse(_soil_payload()))
    result = soil.get_soil(PLACE)
    assert result.ok
    assert result.values["pH"] == 7.2
    assert result.values["Clay"] == 34.0


def test_texture_is_named_from_the_fractions(monkeypatch):
    monkeypatch.setattr(soil.requests, "get",
                        lambda *a, **k: FakeResponse(_soil_payload()))
    assert soil.get_soil(PLACE).texture == "Clay loam"


@pytest.mark.parametrize("clay,sand,silt,expect", [
    (50, 20, 30, "Clay"),
    (30, 50, 20, "Sandy clay loam"),
    (5, 85, 10, "Sand"),
    (10, 80, 10, "Loamy sand"),
    (15, 60, 25, "Sandy loam"),
    (15, 25, 60, "Silt loam"),
    (20, 40, 40, "Loam"),
])
def test_texture_triangle(clay, sand, silt, expect):
    assert soil.classify(clay, sand, silt) == expect


def test_low_organic_carbon_is_called_out(monkeypatch):
    monkeypatch.setattr(soil.requests, "get",
                        lambda *a, **k: FakeResponse(_soil_payload()))
    notes = " ".join(soil.get_soil(PLACE).notes)
    assert "organic carbon" in notes.lower()


def test_soil_http_error_is_explained(monkeypatch):
    monkeypatch.setattr(soil.requests, "get",
                        lambda *a, **k: FakeResponse({}, status=503))
    result = soil.get_soil(PLACE)
    assert not result.ok and "503" in result.error


def test_soil_needs_a_location():
    assert not soil.get_soil(geo.Place("", 0, 0, error="no place")).ok


# ---------------------------------------------------------------- geocoding
GEO_HIT = {"results": [{"name": "Nashik", "latitude": 20.0, "longitude": 73.79,
                        "admin1": "Maharashtra", "admin2": "Nashik",
                        "country": "India"}]}


def test_geocode_reads_the_district_and_state(monkeypatch, tmp_path):
    monkeypatch.setattr(geo, "CACHE_PATH", tmp_path / "places.json")
    monkeypatch.setattr(geo.requests, "get",
                        lambda *a, **k: FakeResponse(GEO_HIT))
    place = geo.find("Nashik")
    assert place.ok and place.district == "Nashik"
    assert place.state == "Maharashtra"


def test_a_place_is_only_looked_up_once(monkeypatch, tmp_path):
    """A village does not move, so the second lookup should be free."""
    monkeypatch.setattr(geo, "CACHE_PATH", tmp_path / "places.json")
    calls = []

    def counting(*a, **k):
        calls.append(1)
        return FakeResponse(GEO_HIT)
    monkeypatch.setattr(geo.requests, "get", counting)

    geo.find("Nashik")
    geo.find("Nashik")
    geo.find("NASHIK")          # and casing should not defeat it
    assert len(calls) == 1


def test_cached_place_survives_losing_the_network(monkeypatch, tmp_path):
    monkeypatch.setattr(geo, "CACHE_PATH", tmp_path / "places.json")
    monkeypatch.setattr(geo.requests, "get", lambda *a, **k: FakeResponse(GEO_HIT))
    geo.find("Nashik")

    def offline(*a, **k):
        raise ConnectionError()
    monkeypatch.setattr(geo.requests, "get", offline)
    assert geo.find("Nashik").ok, "should have come from the cache"


def test_unknown_place_is_reported_not_raised(monkeypatch, tmp_path):
    monkeypatch.setattr(geo, "CACHE_PATH", tmp_path / "places.json")
    monkeypatch.setattr(geo.requests, "get",
                        lambda *a, **k: FakeResponse({"results": []}))
    place = geo.find("Zzzqqq")
    assert not place.ok and "not found" in place.error


def test_empty_query_does_not_call_the_api(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("should not have been called")
    monkeypatch.setattr(geo.requests, "get", boom)
    assert not geo.find("  ").ok


# ------------------------------------------------------------------ weather
def _weather_payload(days=7, rain=0.0):
    return {
        "current": {"temperature_2m": 30.0, "relative_humidity_2m": 60,
                    "precipitation": 0.0, "weather_code": 1,
                    "wind_speed_10m": 8.0},
        "daily": {"time": [f"2026-08-{16+i:02d}" for i in range(days)],
                  "temperature_2m_max": [33.0] * days,
                  "temperature_2m_min": [23.0] * days,
                  "precipitation_sum": [rain] * days,
                  "weather_code": [1] * days},
    }


def test_forecast_is_a_full_week(monkeypatch):
    """Three days decides spraying; seven decides sowing."""
    monkeypatch.setattr(weather.geo, "find", lambda *a, **k: PLACE)
    monkeypatch.setattr(weather.requests, "get",
                        lambda *a, **k: FakeResponse(_weather_payload()))
    w = weather.get_weather("Nashik")
    assert not w.error and len(w.daily) == 7


def test_a_wet_week_warns_against_sowing(monkeypatch):
    monkeypatch.setattr(weather.geo, "find", lambda *a, **k: PLACE)
    monkeypatch.setattr(weather.requests, "get",
                        lambda *a, **k: FakeResponse(_weather_payload(rain=12.0)))
    messages = " ".join(m for _lvl, m in
                        weather.crop_alerts(weather.get_weather("Nashik")))
    assert "Hold off sowing" in messages


def test_a_dry_week_warns_against_rain_fed_sowing(monkeypatch):
    monkeypatch.setattr(weather.geo, "find", lambda *a, **k: PLACE)
    monkeypatch.setattr(weather.requests, "get",
                        lambda *a, **k: FakeResponse(_weather_payload(rain=0.0)))
    messages = " ".join(m for _lvl, m in
                        weather.crop_alerts(weather.get_weather("Nashik")))
    assert "Almost no rain" in messages


def test_weather_failure_is_friendly(monkeypatch):
    monkeypatch.setattr(weather.geo, "find", lambda *a, **k: PLACE)

    def boom(*a, **k):
        raise ConnectionError()
    monkeypatch.setattr(weather.requests, "get", boom)
    assert weather.get_weather("Nashik").error
