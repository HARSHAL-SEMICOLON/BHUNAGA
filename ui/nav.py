"""
Moving between screens.

The navigation lives in the sidebar, as one vertical list with the current
screen highlighted. Earlier versions put five buttons in a row across the top
of the content; that worked, but it pushed the actual page down on a laptop and
gave no room to ever add a sixth.

Two things are deliberate:

  Icons come from Streamlit's Material set (`:material/...`), not emoji. Emoji
  render differently on every device and at every size, which is fine for a
  picture tile a farmer taps and wrong for the chrome around it.

  The word still comes from farmer/text.py. A navigation list that says "Home"
  and "Market" to a Marathi speaker is the same failure as an English answer.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from farmer.text import t


@dataclass(frozen=True)
class Screen:
    key: str
    icon: str          # a Material symbol, for the sidebar
    tile: str          # an emoji, for the big picture tiles a farmer taps


SCREENS: tuple[Screen, ...] = (
    Screen("home", ":material/home:", "🏠"),
    Screen("ask", ":material/forum:", "💬"),
    Screen("diagnose", ":material/photo_camera:", "📷"),
    Screen("today", ":material/wb_sunny:", "🌅"),
    Screen("money", ":material/payments:", "💰"),
    Screen("market", ":material/trending_up:", "📈"),
)

DEFAULT = "home"

# page title and one line of context, per screen
TITLES = {
    "home": ("home.greet", ""),
    "ask": ("ask.head", "home.tagline"),
    "diagnose": ("diag.head", ""),
    "today": ("today.head", "today.hint"),
    "money": ("money.head", ""),
    "market": ("market.head", ""),
}


def current() -> str:
    return st.session_state.get("screen", DEFAULT)


def go(key: str) -> None:
    """
    Send the farmer to another screen.

    st.rerun() matters here. Streamlit has already drawn the old screen by the
    time a button is clicked, so without a rerun the change would not show
    until the farmer touched something else -- which reads as a broken button.
    """
    st.session_state["screen"] = key
    st.rerun()


def sidebar_nav(lang: str = "en") -> None:
    """The main navigation. Drawn inside `with st.sidebar`."""
    here = current()
    with st.container(key="sidenav"):
        for screen in SCREENS:
            clicked = st.button(
                t("nav." + screen.key, lang),
                icon=screen.icon,
                key=f"nav_{screen.key}",
                width="stretch",
                # filled = you are here. not colour alone: the active item is
                # also the only one with a border.
                type="primary" if screen.key == here else "secondary",
            )
            if clicked and screen.key != here:
                go(screen.key)


def title(lang: str) -> tuple[str, str]:
    """The heading and caption for whichever screen we are on."""
    head_key, cap_key = TITLES.get(current(), ("nav.home", ""))
    return t(head_key, lang), (t(cap_key, lang) if cap_key else "")


def back_button(lang: str = "en") -> None:
    """Kept for callers that still want an explicit way home."""
    if st.button(f"⬅️  {t('nav.back', lang)}", key=f"back_{current()}"):
        go("home")
