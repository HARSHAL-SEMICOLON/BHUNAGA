"""
Moving between screens.

The old version used st.tabs plus a list of #anchor links in the sidebar. The
links did nothing at all -- Streamlit renders the page inside its own container
and a bare #hash never scrolls anywhere -- and the tab strip was small text,
which is exactly what a farmer who cannot read cannot use.

So: one place that remembers which screen we are on, and five big buttons that
set it. Every button is an icon first and a word second, and the word comes from
farmer/text.py in the farmer's own language.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from farmer.text import t


@dataclass(frozen=True)
class Screen:
    key: str
    icon: str

    def label(self, lang: str) -> str:
        return f"{self.icon}  {t('nav.' + self.key, lang)}"


SCREENS: tuple[Screen, ...] = (
    Screen("home", "🏠"),
    Screen("ask", "💬"),
    Screen("today", "🌅"),
    Screen("money", "💰"),
    Screen("market", "📈"),
)

DEFAULT = "home"


def current() -> str:
    return st.session_state.get("screen", DEFAULT)


def go(key: str) -> None:
    """
    Send the farmer to another screen.

    st.rerun() matters here. Streamlit has already drawn the old screen by the
    time a button is clicked, so without a rerun the change would not show until
    the farmer touched something else -- which reads as a broken button.
    """
    st.session_state["screen"] = key
    st.rerun()


def bar(lang: str = "en") -> None:
    """The five main buttons. The one you are on is filled in."""
    st.markdown('<div class="mainnav">', unsafe_allow_html=True)
    here = current()
    for column, screen in zip(st.columns(len(SCREENS)), SCREENS):
        with column:
            clicked = st.button(
                screen.label(lang),
                key=f"nav_{screen.key}",
                use_container_width=True,
                # filled = you are here. not colour alone: the filled button is
                # also the only one whose text is light on dark.
                type="primary" if screen.key == here else "secondary",
            )
            if clicked and screen.key != here:
                go(screen.key)
    st.markdown("</div>", unsafe_allow_html=True)


def back_button(lang: str = "en") -> None:
    """A way home from every screen, in the same place every time."""
    if st.button(f"⬅️  {t('nav.back', lang)}", key=f"back_{current()}"):
        go("home")
