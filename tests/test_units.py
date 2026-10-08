"""
Unit tests that try to touch every function we can run without the internet,
the big AI model, or the Qdrant server. Network/model functions are tested on
their safe fallback paths. Run: pytest tests/test_units.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import ingest
from farmer import (answer_writer, cost_calculator, daily_advice,
                    farmer_profile, language_detector, mandi_prices, scoring,
                    text_embedder, vector_database, weather)


# ----------------------------- config ----------------------------- #
def test_config_settings_snapshot():
    assert config.SETTINGS.embed_model == config.EMBED_MODEL_NAME
    assert config.SETTINGS.qdrant_collection == config.QDRANT_COLLECTION


def test_config_datagov_key_always_present():
    # even with no/short user key, a usable key (demo) is set
    assert len(config.DATA_GOV_API_KEY) >= 20


# ----------------------------- ingest ----------------------------- #
def test_ingest_load_text_txt_and_md(tmp_path):
    t = tmp_path / "a.txt"; t.write_text("hello farmer", encoding="utf-8")
    m = tmp_path / "b.md"; m.write_text("# title\nsome text", encoding="utf-8")
    assert "hello farmer" in ingest.load_text(t)
    assert "some text" in ingest.load_text(m)


def test_ingest_load_text_unsupported_returns_empty(tmp_path):
    x = tmp_path / "c.xyz"; x.write_text("nope", encoding="utf-8")
    assert ingest.load_text(x) == ""


def test_ingest_iter_source_files_finds_supported(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "b.png").write_bytes(b"x")
    found = [p.name for p in ingest.iter_source_files(tmp_path)]
    assert "a.txt" in found and "b.png" not in found


def test_ingest_chunk_text_overlap():
    chunks = ingest.chunk_text("y" * 1500)
    assert len(chunks) >= 2 and len(chunks[0]) == config.CHUNK_SIZE


# ----------------------- language_detector ----------------------- #
def test_langdetect_english_and_empty():
    assert language_detector.detect("the quick brown fox jumps over").lang == "en"
    assert language_detector.detect("   ").lang == config.DEFAULT_LANG


# ------------------------- text_embedder ------------------------- #
def test_embedder_sparse_dict_keys_become_int():
    out = text_embedder._to_sparse_dict({"5": 0.3, "9": 0.7})
    assert out == {5: 0.3, 9: 0.7}
    assert all(isinstance(k, int) for k in out)


def test_embedder_embedding_dataclass():
    e = text_embedder.Embedding(dense=[0.1, 0.2], sparse={1: 1.0})
    assert e.dense == [0.1, 0.2] and e.sparse == {1: 1.0}


# ------------------------ vector_database ------------------------ #
def test_vdb_sparse_and_point():
    sv = vector_database.to_sparse_vector({2: 0.5})
    assert list(sv.indices) == [2] and list(sv.values) == [0.5]
    p = vector_database.build_point("x", [0.0]*4, {1: 1.0}, {"text": "t"})
    assert p.payload["text"] == "t"


def test_vdb_ensure_collection_inmemory():
    from qdrant_client import QdrantClient
    c = QdrantClient(location=":memory:")
    vector_database.ensure_collection(c, recreate=True)
    assert c.collection_exists(config.QDRANT_COLLECTION)


# ------------------------- answer_writer ------------------------- #
def test_answer_format_context_and_system_prompt():
    from farmer.searcher import RetrievedChunk
    chunks = [RetrievedChunk("hello", "a.pdf", "en", 0.9)]
    ctx = answer_writer._format_context(chunks)
    assert "a.pdf" in ctx and "hello" in ctx
    assert "Marathi" in answer_writer._system_prompt("Marathi")


def test_answer_generate_strategy_native(monkeypatch):
    from farmer.searcher import RetrievedChunk
    monkeypatch.setattr(answer_writer, "_generate_with_groq",
                        lambda q, c, ln: f"[{ln}] ok")
    monkeypatch.setattr(config, "MARATHI_STRATEGY", "native")
    ans = answer_writer.generate("q", "hi", [RetrievedChunk("t","s","hi",1.0)])
    assert ans.strategy == "native" and "Hindi" in ans.text


# ---------------------------- scoring ---------------------------- #
def test_scoring_norm_contains_and_dict():
    assert scoring._norm("  Hello   WORLD ") == "hello world"
    assert scoring._contains("apply UREA", "urea")
    from farmer.scoring import RetrievalScore
    d = scoring.score_to_dict(RetrievalScore(1, 0.5, 0.5, 0.5, 0))
    assert d["hit_at_k"] == 1 and "keyword_recall" in d


def test_scoring_aggregate():
    assert scoring.aggregate([{"a": 2}, {"a": 4}]) == {"a": 3.0}


# ------------------------- farmer_profile ------------------------ #
def test_profile_summary_and_isset():
    p = farmer_profile.Profile(village="Nashik", crops=["Onion"], soil="Black",
                               land_acres=2)
    assert p.is_set()
    s = p.summary()
    assert "Nashik" in s and "Onion" in s
    assert not farmer_profile.Profile().is_set()


def test_profile_save_load_roundtrip(tmp_path, monkeypatch):
    f = tmp_path / "profile.json"
    monkeypatch.setattr(farmer_profile, "PROFILE_PATH", f)
    p = farmer_profile.Profile(name="Harshal", village="Pune", crops=["Wheat"])
    farmer_profile.save(p)
    loaded = farmer_profile.load()
    assert loaded.name == "Harshal" and loaded.crops == ["Wheat"]


# -------------------------- cost_calculator --------------------- #
def test_cost_compute_profit_and_zero_yield():
    d = cost_calculator.CROP_DEFAULTS["Wheat"]
    r = cost_calculator.compute(d, d["yield"], d["price"], acres=2)
    assert r.total_cost > 0 and r.revenue > 0
    z = cost_calculator.compute(d, 0, d["price"], acres=1)
    assert z.cost_per_unit == 0.0          # no divide-by-zero


def test_cost_defaults_have_all_keys():
    for crop, d in cost_calculator.CROP_DEFAULTS.items():
        for k in cost_calculator.COST_KEYS:
            assert k in d


# --------------------------- weather ---------------------------- #
def test_weather_crop_alerts_rules():
    w = weather.Weather("X", 24, 85, 0, 5, 3, "Cloud", "☁️",
                        daily=[{"date":"d","tmax":26,"tmin":18,"rain":12,"emoji":"🌧️"}])
    levels = [lvl for lvl, _ in weather.crop_alerts(w)]
    assert "warn" in levels   # humid -> fungus warning
    calm = weather.Weather("X", 28, 50, 0, 8, 1, "Clear", "🌤️", daily=[])
    assert weather.crop_alerts(calm)[0][0] == "ok"


def test_weather_get_weather_offline_is_graceful():
    w = weather.get_weather("Pune")     # no internet in CI -> error, not crash
    assert isinstance(w, weather.Weather)
    assert w.error or w.place           # either failed cleanly or worked


def test_weather_code_maps_have_clear():
    assert weather.WCODE[0] == "Clear sky" and 0 in weather.WEMOJI


# ------------------------- mandi_prices ------------------------- #
def test_mandi_sample_and_helpers():
    rows = mandi_prices._sample("Onion")
    assert rows and rows[0]["commodity"] == "Onion"
    recs = mandi_prices._rows_from_records(
        [{"market":"M","commodity":"Onion","min_price":"1","max_price":"2",
          "modal_price":"1.5","arrival_date":"2026-01-01"}])
    assert recs[0]["modal"] == "1.5"


def test_mandi_get_prices_falls_back(monkeypatch):
    # force the live call to fail -> should return cached or sample, never crash
    import requests
    def boom(*a, **k): raise requests.exceptions.Timeout()
    monkeypatch.setattr(requests, "get", boom)
    res = mandi_prices.get_prices("Onion")
    assert res.source in ("cached", "sample") and res.rows


def test_mandi_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(mandi_prices, "CACHE_PATH", tmp_path / "m.json")
    mandi_prices._save_cache("Onion", [{"market": "M", "modal": 1500}])
    got = mandi_prices._load_cache("Onion")
    assert got and got["rows"][0]["modal"] == 1500


# -------------------------- daily_advice ------------------------ #
def test_daily_advice_resolve_lang():
    assert daily_advice._resolve_lang(farmer_profile.Profile(language="mr")) == "mr"
    assert daily_advice._resolve_lang(farmer_profile.Profile(language="auto")) == "en"


def _stub_briefing_sources(monkeypatch):
    """
    Cut every wire to the outside world.

    The briefing now pulls weather, the spray window and the soil, so a test
    that only stubbed the weather would quietly make three real network calls.
    """
    monkeypatch.setattr(daily_advice.weather, "get_weather",
        lambda loc, lang="en": weather.Weather(
            "Pune", 30, 60, 0, 8, 1, "Clear", "🌤️",
            daily=[{"date": "d", "tmax": 32, "tmin": 20,
                    "rain": 0, "emoji": "🌤️"}]))
    monkeypatch.setattr(daily_advice.geo, "find",
                        lambda name, lang="en": daily_advice.geo.Place(
                            name="Pune", lat=18.5, lon=73.9))
    monkeypatch.setattr(daily_advice.spray, "get_advice",
                        lambda place: daily_advice.spray.SprayAdvice(
                            error="not needed in this test"))
    monkeypatch.setattr(daily_advice.soil, "get_soil",
                        lambda place: daily_advice.soil.Soil(
                            error="not needed in this test"))


def test_daily_advice_build_returns_card(monkeypatch):
    _stub_briefing_sources(monkeypatch)
    monkeypatch.setattr(daily_advice.answer_writer, "llm_text",
                        lambda s, u, max_tokens=500: "Do field work today.")
    out = daily_advice.build(farmer_profile.Profile(village="Pune", language="en"))
    assert "weather" in out and "text" in out and out["text"]


def test_daily_advice_survives_the_model_being_down(monkeypatch):
    """The rule-based alerts are real advice, not a placeholder."""
    _stub_briefing_sources(monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("no API key")
    monkeypatch.setattr(daily_advice.answer_writer, "llm_text", boom)

    out = daily_advice.build(farmer_profile.Profile(village="Pune", language="en"))
    assert out["text"] and out["text"] == out["rule_text"]


def test_daily_advice_hands_the_spray_hours_over_as_fact(monkeypatch):
    """
    The safe hours are computed from the hourly forecast, not reasoned out by
    the model. The prompt must therefore contain them already worked out.
    """
    from datetime import datetime
    _stub_briefing_sources(monkeypatch)

    def window(hour):
        return daily_advice.spray.Hour(time=datetime(2026, 8, 16, hour),
                                       wind=6.0, rain_chance=0, temp=28.0,
                                       humidity=55, score=95)
    monkeypatch.setattr(daily_advice.spray, "get_advice",
                        lambda place: daily_advice.spray.SprayAdvice(
                            hours=[window(9), window(10)],
                            best=[window(9), window(10)]))

    seen = {}
    monkeypatch.setattr(daily_advice.answer_writer, "llm_text",
                        lambda s, u, max_tokens=500: seen.update(prompt=u) or "ok")
    daily_advice.build(farmer_profile.Profile(village="Pune", language="en"))

    assert "SPRAYING" in seen["prompt"]
    assert "09:00" in seen["prompt"], "the hours must be given, not inferred"
