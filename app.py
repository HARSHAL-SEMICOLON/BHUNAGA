#!/usr/bin/env python3
"""
Bhunaga (भुनागा) — Farmer's Best Friend.

This file only wires things together: set up the page, draw the sidebar, work
out which screen we are on, and hand over to it. The screens themselves live in
ui/, and everything they call lives in farmer/.

Run it with:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from farmer import farmer_profile as profile_mod
from farmer import text as strings
from ui import ask, home, nav, sidebar, theme, tools

st.set_page_config(page_title="Bhunaga - भुनागा", page_icon="🪱", layout="wide")
theme.apply()


def _state():
    """Everything that has to survive a rerun, created once."""
    if "history" not in st.session_state:
        st.session_state["history"] = []
    if "profile" not in st.session_state:
        st.session_state["profile"] = profile_mod.load()
    if "screen" not in st.session_state:
        st.session_state["screen"] = nav.DEFAULT


def main() -> None:
    _state()

    # "auto" is a fine setting for answering — we work the language out from the
    # question — but the interface has to be written in some actual language, so
    # the labels fall back to English.
    profile = st.session_state["profile"]
    auto = profile.language not in strings.LANGS
    ui_lang = strings.resolve(profile.language)

    profile, kb_count = sidebar.render(profile, ui_lang)
    st.session_state["profile"] = profile

    nav.bar(ui_lang)
    screen = nav.current()

    if screen == "home":
        home.render(ui_lang)
        return

    # every screen except home gets a way back, in the same place each time
    nav.back_button(ui_lang)

    if screen == "ask":
        ask.render(ui_lang, kb_count, detect=auto)
    elif screen == "today":
        tools.today(profile, ui_lang)
    elif screen == "money":
        tools.money(profile, ui_lang)
    elif screen == "market":
        tools.market(profile, ui_lang)
    else:
        nav.go("home")


if __name__ == "__main__":
    main()
