"""
The landing screen.

Shaped around one question: what does a farmer who has just opened this on a
phone, standing in a field, actually need in the first three seconds?

  1. a way in that needs no reading      — the four picture tiles
  2. proof it speaks their language      — the hero, in their language
  3. something to tap without thinking   — the questions others ask most
  4. their own farm, not a generic one   — the overview panel

Everything below that is teaching material and is allowed to be scrolled past.

Not one English word is written in this file. Every string comes from
farmer/text.py, because the screen that changes when you switch language has
to be the whole screen, not just the five buttons at the top.
"""

from __future__ import annotations

import streamlit as st

from farmer import question_bank
from farmer.text import t
from ui import nav, theme, warli

# screen key -> the icon on its tile. the words come from farmer/text.py
TILES = [("ask", "💬"), ("diagnose", "📷"), ("today", "🌅"),
         ("money", "💰"), ("market", "📈")]


def _hero(lang: str) -> None:
    """Title, tagline, and three chips saying what this thing can do."""
    chips = [
        ("🌐", t("home.chip_lang", lang), t("home.chip_lang_s", lang)),
        ("📄", t("home.chip_src", lang), t("home.chip_src_s", lang)),
        ("🎤", t("home.chip_voice", lang), t("home.chip_voice_s", lang)),
    ]
    cells = "".join(
        f'<div class="chip"><span class="ci">{icon}</span>'
        f'<span class="ct"><b>{title}</b><i>{sub}</i></span></div>'
        for icon, title, sub in chips)
    st.markdown(
        warli.defs()
        + f'<div class="hero rise">'
        f'  {warli.watermark()}'
        f'  <h1>{t("home.hero", lang)}</h1>'
        f'  <div class="mr">भुनागा — शेतकऱ्याचा सर्वोत्तम मित्र</div>'
        f'  <p>{t("home.tagline", lang)}</p>'
        f'  <div class="chips">{cells}</div>'
        f'  {warli.band(18)}'
        f'</div>', unsafe_allow_html=True)


def _quick_ask(lang: str) -> None:
    """
    The shortest path from landing here to an actual answer.

    One box, one button, straight into the Ask screen with the question
    already loaded. A farmer who knows what they want should not have to find
    the navigation first.
    """
    box, send = st.columns([5, 1], vertical_alignment="bottom")
    with box:
        typed = st.text_input(t("ask.type", lang), key="home_ask",
                              placeholder="…", label_visibility="collapsed")
    with send:
        go = st.button(t("ask.button", lang), type="primary",
                       width="stretch", key="home_ask_go")
    if go and typed.strip():
        st.session_state["pending_question"] = typed.strip()
        nav.go("ask")


def _weather_strip(profile, lang: str) -> None:
    """
    Today's conditions for the farmer's own village, if we know it.

    Wrapped end to end: the landing screen must not hang or blow up because a
    weather host is slow. No village, no call. Call fails, the strip is simply
    not drawn -- Today carries the full version with its own error states.
    """
    place = (profile.village or profile.district or "").strip() if profile else ""
    if not place:
        return
    try:
        from ui.tools import _weather          # cached for 15 minutes
        w = _weather(place, lang)
    except Exception:
        return
    if getattr(w, "error", None):
        return

    st.markdown(f"##### {w.emoji} {w.place} — {w.desc}")
    cells = st.columns(4)
    cells[0].metric(t("today.temp", lang), f"{w.temp:.0f}°C")
    cells[1].metric(t("today.humidity", lang), f"{w.humidity}%")
    cells[2].metric(t("today.rain", lang), f"{w.precip:.1f} mm")
    cells[3].metric(t("today.wind", lang), f"{w.wind:.0f} km/h")


def _tiles(lang: str) -> None:
    """
    The four big ways in.

    The icon and the word are the button's own label, so the whole card is the
    tap target. An earlier version drew a styled div and put a separate button
    underneath it, which read as two controls and left the pretty half dead.
    """
    st.markdown(f"#### {t('home.quick', lang)}")
    # st.container(key=...) is the only way to get a class onto the element
    # that actually wraps the widgets. A bare st.markdown("<div>") renders as
    # a sibling, so the buttons would fall outside it and the CSS would miss.
    with st.container(key="hometiles"):
        for column, (screen, icon) in zip(st.columns(len(TILES)), TILES):
            with column:
                if st.button(f'{icon}\n\n{t("home." + screen, lang)}',
                             key=f"tile_{screen}", width="stretch"):
                    nav.go(screen)


def _popular(lang: str) -> None:
    """
    The first question from each topic, as one tap each.

    These come straight out of the question bank, so they are already written
    in all three languages and already match something the documents can
    answer. Tapping one fills the Ask box and goes there — the farmer never
    sees an empty text field.
    """
    st.markdown(f"##### 🔥 {t('home.popular', lang)}")
    picks = [topic.questions[0] for topic in question_bank.TOPICS
             if topic.questions][:5]
    with st.container(key="popq"):
        for i, q in enumerate(picks):
            if st.button(f"{q.icon}  {q.text(lang)}", key=f"pop_{i}",
                         width="stretch"):
                st.session_state["pending_question"] = q.text(lang)
                nav.go("ask")


def _farm(profile, lang: str) -> None:
    """Whatever the farmer has told us about their own land."""
    st.markdown(f"##### 🧑‍🌾 {t('home.farm', lang)}")

    rows = []
    place = profile.village or profile.district
    if place:
        both = ", ".join(x for x in (profile.village, profile.district) if x)
        rows.append(("📍", t("home.farm_place", lang), both))
    if profile.crops:
        rows.append(("🌾", t("home.farm_crops", lang), ", ".join(profile.crops)))
    if profile.soil:
        rows.append(("🟫", t("home.farm_soil", lang), profile.soil))
    if profile.land_acres:
        rows.append(("📐", t("home.farm_land", lang),
                     f"{profile.land_acres:g} {t('home.acres', lang)}"))

    if not rows:
        st.markdown(f'<div class="panel empty">{t("home.farm_empty", lang)}</div>',
                    unsafe_allow_html=True)
        return

    body = "".join(
        f'<div class="prow"><span class="pi">{icon}</span>'
        f'<span class="pk">{label}</span><span class="pv">{value}</span></div>'
        for icon, label, value in rows)
    st.markdown(f'<div class="panel">{body}</div>', unsafe_allow_html=True)


def _why(lang: str) -> None:
    cards = [("🌱", "why1"), ("🧪", "why2"), ("💧", "why3"), ("🌾", "why4")]
    st.markdown(f"## {t('home.why', lang)}")
    st.markdown(
        '<div class="grid grid2 rise">'
        + "".join(f'<div class="card"><div class="ic">{icon}</div>'
                  f'<h4>{t("home." + key, lang)}</h4>'
                  f'<p>{t("home." + key + "d", lang)}</p></div>'
                  for icon, key in cards)
        + "</div>", unsafe_allow_html=True)


def _friends(lang: str) -> None:
    friends = [("🪱", "fr1"), ("🐄", "fr2"), ("🐝", "fr3"), ("🐂", "fr4")]
    st.markdown(
        f'<div class="friends rise"><h2>🤝 {t("home.friends", lang)}</h2>'
        '<div class="grid">'
        + "".join(f'<div class="friend"><div class="e">{icon}</div>'
                  f'<h4>{t("home." + key, lang)}</h4>'
                  f'<p>{t("home." + key + "d", lang)}</p></div>'
                  for icon, key in friends)
        + "</div></div>", unsafe_allow_html=True)


def _soil(lang: str) -> None:
    """
    Five fixed bars.

    They are hard-coded in this file and they are not a reading from anyone's
    field. The caption says so, because a farmer acting on an invented nitrogen
    figure buys the wrong fertiliser. Real measured values for a real location
    are on the Today screen, from SoilGrids.
    """
    st.markdown(f"## 📊 {t('home.soil', lang)}")
    st.caption(t("home.soil_note", lang))
    bars = [("s_n", 85), ("s_air", 92), ("s_wet", 78), ("s_yield", 70),
            ("s_org", 88)]
    for key, value in bars:
        st.markdown(f'<div class="soil-row">{t("home." + key, lang)} — {value}%</div>',
                    unsafe_allow_html=True)
        st.progress(value / 100)


def render(lang: str, profile=None) -> None:
    _hero(lang)
    _quick_ask(lang)
    _tiles(lang)
    if profile is not None:
        _weather_strip(profile, lang)

    st.markdown(f'<div class="ticker"><span>{t("home.ticker", lang)}</span></div>',
                unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="medium")
    with left:
        _popular(lang)
    with right:
        if profile is not None:
            _farm(profile, lang)

    # Four Warli panels, drawn in the page. These replaced four hotlinked
    # stock photographs -- an English allotment, a European market stall, a
    # trowel in compost and a wheat field -- none of which were Indian, and
    # all of which were megabytes over a farmer's connection.
    st.markdown(
        '<div class="grid rise">'
        + "".join(warli.panel(scene, t("art." + scene, lang))
                  for scene in ("plough", "sow", "rain", "harvest"))
        + "</div>", unsafe_allow_html=True)

    st.markdown(f'<div class="wdiv">{warli.band(22)}</div>',
                unsafe_allow_html=True)
    _why(lang)
    _friends(lang)
    _soil(lang)

    st.markdown(
        f'<div class="footwrap">{warli.band(26)}'
        '<div class="footer"><b>🪱 Bhunaga</b> — भुनागा, शेतकऱ्याचा सर्वोत्तम मित्र<br>'
        f'{t("home.footer", lang)}</div></div>', unsafe_allow_html=True)
