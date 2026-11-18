"""
हमीभाव — the guaranteed floor price.

Two classes of test matter here. The figures themselves, because a wrong MSP
is a farmer selling below the floor believing they are above it. And the
absences, because telling someone their onion has no floor is the whole point
of asking.
"""

from __future__ import annotations

import pytest

from farmer import msp


# ───────────────── the figures, against the announcements ──────────────────

@pytest.mark.parametrize("crop,variety,price", [
    # Kharif, CCEA 13 May 2026, marketing season 2026-27
    ("Paddy", "common", 2441), ("Paddy", "Grade A", 2461),
    ("Tur", "", 8450), ("Moong", "", 8780), ("Urad", "", 8200),
    ("Soybean", "yellow", 5708), ("Groundnut", "", 7517),
    ("Cotton", "medium staple", 8267), ("Cotton", "long staple", 8667),
    ("Maize", "", 2410), ("Bajra", "", 2900),
    # Rabi, Cabinet 30 September 2026, marketing season 2027-28
    ("Wheat", "", 2610), ("Gram", "", 5958), ("Mustard", "", 6613),
    ("Lentil", "", 7390), ("Barley", "", 2286), ("Safflower", "", 7215),
])
def test_the_announced_figure_is_what_is_stored(crop, variety, price):
    rows = [r for r in msp.TABLE if r.crop == crop and r.variety == variety]
    assert len(rows) == 1, f"{crop} {variety}"
    assert rows[0].price == price


def test_every_row_says_where_it_came_from():
    """An unsourced price in an advisory app is a rumour."""
    for row in msp.TABLE:
        assert row.source and row.season
        assert row.mechanism in ("MSP", "FRP")


def test_every_row_is_a_sane_price():
    for row in msp.TABLE:
        assert 100 < row.price < 20000, row.label


# ───────────────── finding a crop by whatever it is called ─────────────────

@pytest.mark.parametrize("typed,expect", [
    ("Wheat", "Wheat"), ("wheat", "Wheat"), ("  WHEAT  ", "Wheat"),
    ("गहू", "Wheat"), ("गेहूं", "Wheat"),
    ("कापूस", "Cotton"), ("kapus", "Cotton"), ("cotton", "Cotton"),
    ("ऊस", "Sugarcane"), ("sugarcane", "Sugarcane"),
    ("तूर", "Tur"), ("arhar", "Tur"), ("pigeonpea", "Tur"),
    ("हरभरा", "Gram"), ("chana", "Gram"),
    ("soyabean", "Soybean"), ("सोयाबीन", "Soybean"),
])
def test_a_crop_is_found_by_the_name_the_farmer_uses(typed, expect):
    assert msp.canonical(typed) == expect


def test_a_crop_with_grades_returns_all_of_them():
    rows = msp.for_crop("cotton")
    assert {r.variety for r in rows} == {"medium staple", "long staple"}


@pytest.mark.parametrize("junk", ["", "   ", None, "spaceship", "12345"])
def test_nonsense_does_not_raise(junk):
    assert msp.canonical(junk) == ""
    assert msp.for_crop(junk) == []


# ───────────────────────── the absences ────────────────────────────────────

@pytest.mark.parametrize("crop", ["Onion", "onion", "Tomato", "Potato", "Grapes"])
def test_a_crop_with_no_floor_says_so_plainly(crop):
    """
    Silence here would be read as "the app does not know". The farmer needs
    to hear that there is no floor, which is a different and costlier fact.
    """
    assert msp.for_crop(crop) == []
    assert msp.has_no_floor(crop) is True


def test_an_unknown_crop_is_not_mistaken_for_one_without_a_floor():
    assert msp.for_crop("dragon fruit") == []
    assert msp.has_no_floor("dragon fruit") is False


# ───────────────────────── sugarcane is not MSP ────────────────────────────

def test_sugarcane_is_marked_as_frp_not_msp():
    row = msp.for_crop("sugarcane")[0]
    assert row.mechanism == "FRP"
    assert row.price == 365
    assert "recovery" in row.note.lower()


@pytest.mark.parametrize("recovery,expected", [
    (10.25, 365.00),     # the benchmark itself
    (10.35, 368.56),     # one step above
    (10.15, 361.44),     # one step below
    (11.25, 400.60),     # ten steps above
])
def test_frp_moves_with_the_mills_recovery(recovery, expected):
    assert msp.frp_for_recovery(recovery) == pytest.approx(expected, abs=0.01)


def test_a_low_recovery_mill_pays_the_floor_not_less():
    """Below 9.5% the deduction stops; it does not keep falling."""
    assert msp.frp_for_recovery(9.4) == 338.30
    assert msp.frp_for_recovery(8.0) == 338.30
    assert msp.frp_for_recovery(0) == 338.30


# ───────────────────────── comparing to the market ─────────────────────────

def test_a_price_under_the_floor_is_reported_as_under():
    c = msp.compare(7000, msp.for_crop("Tur")[0])
    assert c.below
    assert c.gap == pytest.approx(-1450)
    assert c.percent < 0


def test_a_price_over_the_floor_is_not():
    c = msp.compare(9000, msp.for_crop("Tur")[0])
    assert not c.below
    assert c.gap == pytest.approx(550)


def test_a_price_exactly_at_the_floor_is_not_below_it():
    c = msp.compare(8450, msp.for_crop("Tur")[0])
    assert not c.below
    assert c.gap == 0
