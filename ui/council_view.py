"""
Drawing the council's deliberation.

Two decisions worth knowing about.

The disagreements are printed *outside* the expander. If two experts give
different fertiliser doses, that is the single most important thing on the
screen and burying it behind a click would be dishonest.

And we show both agreement numbers -- the chairman's own and the word overlap we
measured ourselves. If the chairman claims 95 while the opinions barely share a
word, you can see it.
"""

from __future__ import annotations

import html
import re

import streamlit as st

from farmer.text import t


def payload(panel) -> dict:
    """
    Flatten a Council into a plain dict.

    The chat history has to survive a rerun and stay easy to draw, and a dict of
    strings does that better than a graph of dataclasses.
    """
    v = panel.verdict
    return {
        "score": v.score, "label": v.label, "conflicts": v.conflicts,
        "basis": v.basis, "chairman_score": v.chairman_score,
        "word_overlap": v.word_overlap, "spoke": len(v.spoke),
        "seats": [{"icon": op.seat.icon, "title": op.seat.title,
                   "title_mr": op.seat.title_mr, "text": op.text,
                   "abstained": op.abstained, "failed": op.failed}
                  for op in panel.opinions],
    }


def _as_html(text: str) -> str:
    """
    The experts write markdown, but it sits inside our own HTML card where
    Streamlit will not touch it. So we convert the two things they actually
    use -- bullets and bold -- and escape everything else.
    """
    safe = html.escape(text)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
    lines = []
    for line in safe.splitlines():
        line = line.strip()
        if not line:
            continue
        lines.append(f"• {line.lstrip('-*').strip()}" if line[0] in "-*" else line)
    return "<br>".join(lines)


def render(council: dict, lang: str = "en") -> None:
    st.markdown(
        f'<div class="consensus">'
        f'<span class="lbl">🏛️ {t("council." + council["label"], lang)}</span>'
        f'<span class="meter m-{council["label"]}">'
        f'<i style="width:{council["score"]}%"></i></span>'
        f'<span class="lbl">{council["score"]}/100</span>'
        f'<span class="note">{council["spoke"]} / 3</span></div>',
        unsafe_allow_html=True)

    # a disagreement is the one thing the farmer must not have to click for
    for clash in council["conflicts"]:
        st.markdown(f'<div class="clash">⚠️ {t("council.clash", lang)} '
                    f'{html.escape(clash)}</div>', unsafe_allow_html=True)

    with st.expander(t("council.how", lang)):
        cards = []
        for seat in council["seats"]:
            if seat["failed"]:
                css, body = "seat broke", t("council.broke", lang)
            elif seat["abstained"]:
                css, body = "seat quiet", t("council.quiet", lang)
            else:
                css, body = "seat", _as_html(seat["text"])
            cards.append(
                f'<div class="{css}"><h5>{seat["icon"]} {seat["title"]}'
                f'<br><span style="font-size:.8rem;font-weight:400">'
                f'{seat["title_mr"]}</span></h5>'
                f'<div class="body">{body}</div></div>')
        st.markdown(f'<div class="seats">{"".join(cards)}</div>',
                    unsafe_allow_html=True)

        if council["basis"]:
            st.markdown(f'<div class="gavel"><b>Chairman:</b> '
                        f'{html.escape(council["basis"])}</div>',
                        unsafe_allow_html=True)
        st.caption(
            f"The chairman scored the agreement {council['chairman_score']}/100. "
            f"Measured separately, the opinions shared "
            f"{council['word_overlap']:.0%} of their words. The bar blends the "
            f"two, 70/30.")
