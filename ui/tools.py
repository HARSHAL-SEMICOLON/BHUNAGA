"""
The three practical screens: Today, Money, Market.

They live together because each is short and they share the same shape — take a
little input, call one thing in farmer/, show the result.

Today is the busiest of the three. It carries the weather, the week ahead, the
spraying window and the soil, because those four are the things a farmer wants
before walking out to the field, and making them four separate screens would
mean four taps to learn one morning's worth of information.
"""

from __future__ import annotations

import streamlit as st

import config
from farmer import (cost_calculator, daily_advice, geo, mandi_prices, soil,
                    spray, weather)
from farmer.text import t
from ui import speak


@st.cache_data(ttl=900, show_spinner=False)
def _weather(city, lang):
    return weather.get_weather(city, lang)


@st.cache_data(ttl=1800, show_spinner=False)
def _place(city, lang):
    return geo.find(city, lang)


@st.cache_data(ttl=3600, show_spinner=False)
def _spray(lat, lon, name):
    # cached on the coordinates rather than the Place object, because Streamlit
    # needs the arguments to be hashable
    return spray.get_advice(geo.Place(name=name, lat=lat, lon=lon))


@st.cache_data(ttl=86400, show_spinner=False)
def _soil(lat, lon, name):
    # soil does not change day to day, so this one is cached for a whole day
    return soil.get_soil(geo.Place(name=name, lat=lat, lon=lon))


def _show_weather(w, lang: str) -> None:
    if w.error:
        st.info(f"🌦️ {w.error}")
        return
    st.markdown(f"##### {w.emoji} {w.place} — {w.desc}")
    columns = st.columns(4)
    columns[0].metric(t("today.temp", lang), f"{w.temp:.0f}°C")
    columns[1].metric(t("today.humidity", lang), f"{w.humidity}%")
    columns[2].metric(t("today.rain", lang), f"{w.precip:.1f} mm")
    columns[3].metric(t("today.wind", lang), f"{w.wind:.0f} km/h")

    if w.daily:
        st.markdown(f"**{t('today.week', lang)}**")
        for column, day in zip(st.columns(len(w.daily)), w.daily):
            column.markdown(
                f'<div class="day"><div class="d">{day["date"][5:]}</div>'
                f'<div class="e">{day["emoji"]}</div>'
                f'<div class="t">{day["tmax"]:.0f}° / {day["tmin"]:.0f}°</div>'
                f'<div class="r">💧 {day["rain"]:.0f} mm</div></div>',
                unsafe_allow_html=True)


def _show_spray(place, lang: str) -> None:
    st.markdown(f"#### 💨 {t('spray.head', lang)}")
    st.caption(t("spray.why", lang))

    if not place.ok:
        st.info(place.error)
        return
    if not st.button(t("spray.check", lang), use_container_width=True,
                     key="spray_btn"):
        return

    advice = _spray(place.lat, place.lon, place.name)
    if not advice.ok:
        st.info(advice.error)
        return

    windows = advice.windows()
    if not windows:
        st.warning(f"🚫 {t('spray.none', lang)}")
        return

    st.success(f"✅ {spray.summarise(advice)}")
    st.markdown(f"**{t('spray.good', lang)}**")
    for start, end in windows:
        hours = int((end.time - start.time).total_seconds() // 3600) + 1
        st.markdown(
            f'<div class="window"><b>{start.time.strftime("%A")} '
            f'{start.time.strftime("%H:%M")}–{end.time.strftime("%H:%M")}</b>'
            f' · {hours} h · wind {start.wind:.0f}–{end.wind:.0f} km/h</div>',
            unsafe_allow_html=True)

    # the bad hours are worth showing too, so the farmer can see it is not
    # arbitrary — every rejected hour says exactly why it was rejected
    with st.expander("🕐 Every hour, and why"):
        for hour in advice.hours:
            mark = "✅" if hour.good else "❌"
            why = "; ".join(hour.reasons) if hour.reasons else "good conditions"
            st.markdown(f"{mark} **{hour.label}** · {hour.score}/100 · {why}")


def _show_soil(place, lang: str) -> None:
    st.markdown(f"#### 🟫 {t('soil.head', lang)}")
    if not place.ok:
        st.info(place.error)
        return
    if not st.button(t("soil.check", lang), use_container_width=True,
                     key="soil_btn"):
        return

    with st.spinner(t("soil.working", lang)):
        result = _soil(place.lat, place.lon, place.name)
    if not result.ok:
        st.info(result.error)
        return

    if result.texture:
        st.markdown(f"##### {t('soil.texture', lang)}: **{result.texture}**")
    columns = st.columns(min(4, len(result.values)) or 1)
    for i, (label, value) in enumerate(result.values.items()):
        columns[i % len(columns)].metric(label, value)
    for note in result.notes:
        st.markdown(f'<div class="card">{note}</div>', unsafe_allow_html=True)
    st.caption(soil.DISCLAIMER)


def today(profile, lang: str = "en") -> None:
    st.markdown(f"### 🌅 {t('today.head', lang)}")
    place_name = st.text_input(t("today.place", lang),
                               profile.village or profile.district or "Pune")

    if place_name:
        _show_weather(_weather(place_name, lang), lang)

    if st.button(t("today.generate", lang), type="primary",
                 use_container_width=True):
        if not config.GROQ_API_KEY:
            st.error(t("common.nokey", lang))
        else:
            with st.spinner(t("today.working", lang)):
                brief = daily_advice.build(profile)
            st.markdown(f'<div class="card">{brief["text"]}</div>',
                        unsafe_allow_html=True)
            speak.button(brief["text"], lang, key="today")
            for _level, message in brief["alerts"]:
                st.markdown(f"- {message}")
    else:
        st.caption(t("today.hint", lang))

    if place_name:
        place = _place(place_name, lang)
        st.divider()
        _show_spray(place, lang)
        st.divider()
        _show_soil(place, lang)


def money(profile, lang: str = "en") -> None:
    st.markdown(f"### 💰 {t('money.head', lang)}")
    crop = st.selectbox(t("money.crop", lang),
                        list(cost_calculator.CROP_DEFAULTS.keys()))
    defaults = cost_calculator.CROP_DEFAULTS[crop]
    acres = st.number_input(t("money.area", lang), 0.25, 10000.0,
                            float(profile.land_acres or 1.0), step=0.25)

    columns, costs = st.columns(3), {}
    for i, key in enumerate(cost_calculator.COST_KEYS):
        costs[key] = columns[i % 3].number_input(
            key.capitalize(), 0.0, 1e7, float(defaults[key]), step=500.0,
            key=f"cost_{key}")

    left, right = st.columns(2)
    yield_per_acre = left.number_input(
        f"{t('money.yield', lang)} ({defaults['yield_unit']})", 0.0, 1e6,
        float(defaults["yield"]), step=1.0)
    price = right.number_input(
        f"{t('money.price', lang)} (₹/{defaults['yield_unit']})", 0.0, 1e7,
        float(defaults["price"]), step=50.0)

    if st.button(t("money.calculate", lang), type="primary",
                 use_container_width=True):
        result = cost_calculator.compute(costs, yield_per_acre, price, acres,
                                         defaults["yield_unit"])
        metrics = st.columns(3)
        metrics[0].metric(t("money.total", lang), f"₹{result.total_cost:,.0f}")
        metrics[1].metric(t("money.revenue", lang), f"₹{result.revenue:,.0f}")
        # an arrow as well as a colour, for anyone who cannot tell red from green
        won = result.profit >= 0
        metrics[2].metric(
            t("money.profit", lang), f"₹{result.profit:,.0f}",
            delta=f"{'📈' if won else '📉'} "
                  f"{t('money.gain' if won else 'money.loss', lang)}")
        st.bar_chart(result.breakdown)


COMMON_CROPS = ["Onion", "Tomato", "Potato", "Cotton", "Soybean", "Wheat",
                "Grapes", "Sugarcane", "Tur", "Gram"]


def market(profile, lang: str = "en") -> None:
    st.markdown(f"### 📈 {t('market.head', lang)}")
    left, middle, right = st.columns(3)
    commodity = left.selectbox(t("market.commodity", lang), COMMON_CROPS)
    state = middle.text_input(t("market.state", lang), "Maharashtra")
    district = right.text_input(t("market.district", lang), profile.district)

    if st.button(t("market.get", lang), type="primary",
                 use_container_width=True):
        with st.spinner(t("market.working", lang)):
            result = mandi_prices.get_prices(commodity, state, district)

        if result.error:
            st.warning(f"⚠️ {result.error}")
        else:
            badge = t(f"market.{result.source}", lang)
            # sample prices get a loud warning, not a quiet grey note. a farmer
            # who sells against a placeholder number loses real money.
            if result.source == "sample":
                st.error(f"**{badge}**")
            elif result.source == "cached":
                st.warning(f"**{badge}**")
            else:
                st.success(f"**{badge}**")
            st.caption(f"{len(result.rows)} records · {t('market.unit', lang)}")
            if result.note:
                st.info(result.note)
            st.dataframe(result.rows, use_container_width=True, hide_index=True)

    st.caption("Live data from data.gov.in (Agmarknet).")
    with st.expander("🔧 Why am I not seeing live prices?"):
        st.markdown(
            "Run `python check_apis.py --raw` in the project folder. It prints "
            "exactly what the price API returned and which filter style worked, "
            "which is far quicker than guessing.\n\n"
            "The most common cause is the shared demo key being rate limited. "
            "A free personal key from "
            "[data.gov.in](https://data.gov.in/help/how-use-datasets-apis) "
            "fixes it — put it in `.env` as `DATA_GOV_API_KEY`.")
