"""
The crop check screen: photograph a sick plant, get a grounded second opinion.

The order on screen is the order of confidence, and it is deliberate.

  1. what the photo shows      -- observation, the model's strongest ground
  2. possible causes           -- with honest confidence, plural on purpose
  3. what the documents say    -- retrieved, cited, the only treatment advice
  4. confirm with a human      -- always, never dismissible

If the model is not confident enough to name anything, the screen stops after
step 2 and asks for a better photograph. It does not fall back to "it might be
early blight, try mancozeb" -- that sentence is how a farmer ends up spraying
a fungicide at a nitrogen deficiency.
"""

from __future__ import annotations

import streamlit as st

import config
from farmer import answer_writer, crop_vision, searcher
from farmer.text import t
from ui import speak


def _confidence_bar(candidate, strongest: bool) -> str:
    """A labelled bar. Never colour alone -- the number is always written."""
    tone = "m-strong" if candidate.confidence >= config.VISION_MIN_CONFIDENCE \
        else "m-partial"
    weight = "700" if strongest else "500"
    return (
        f'<div class="consensus">'
        f'<span class="lbl" style="font-weight:{weight}">{candidate.name}</span>'
        f'<span class="meter {tone}"><i style="width:{candidate.confidence}%"></i></span>'
        f'<span class="note">{candidate.confidence}%</span>'
        f'</div>')


def _observation(obs, lang: str) -> None:
    st.markdown(f"##### 🔍 {t('diag.seen', lang)}")

    facts = []
    if obs.crop:
        facts.append(f"**{obs.crop}**")
    if obs.plant_part:
        facts.append(obs.plant_part)
    if facts:
        st.markdown(" · ".join(facts))

    if obs.visible:
        st.markdown("\n".join(f"- {v}" for v in obs.visible))
    if obs.photo_problem:
        st.warning(f"📷 {obs.photo_problem}")


def _causes(obs, lang: str) -> None:
    if not obs.candidates:
        return
    st.markdown(f"##### 🤔 {t('diag.maybe', lang)}")
    for i, candidate in enumerate(obs.candidates):
        st.markdown(_confidence_bar(candidate, strongest=(i == 0)),
                    unsafe_allow_html=True)
    tells = [c for c in obs.candidates if c.tells]
    if tells:
        with st.expander(f"🔬 {t('diag.tells', lang)}"):
            for candidate in tells:
                st.markdown(f"**{candidate.name}** — {candidate.tells}")


def _guidance(obs, lang: str, kb_count: int) -> None:
    """
    The only part of this screen that gives advice, and it comes from the
    documents rather than from the photograph.
    """
    if kb_count <= 0:
        st.info(t("ask.empty", lang))
        return

    query = obs.search_query()
    if not query:
        return

    with st.spinner(t("ask.panel" if config.COUNCIL_ENABLED else "ask.thinking", lang)):
        try:
            chunks = searcher.retrieve(query, query_lang=lang)
        except Exception as exc:
            st.info(f"Could not search the documents ({type(exc).__name__}).")
            return

        if not chunks:
            st.info(t("ask.nothing", lang))
            return

        asked = (
            f"A farmer has photographed a plant. Visible: "
            f"{'; '.join(obs.visible) or 'not described'}. "
            f"Crop: {obs.crop or 'unknown'}. "
            f"The most likely cause from the photograph is "
            f"{obs.best.name} ({obs.best.confidence}% confidence).\n\n"
            f"Using only the documents, explain what to do about this. State "
            f"any dose exactly as the document gives it. If the documents do "
            f"not cover this, say so rather than filling the gap."
        )
        try:
            written = answer_writer.generate(asked, query_lang=lang, chunks=chunks)
        except Exception as exc:
            st.info(f"Could not write the guidance ({str(exc)[:140]})")
            return

    st.markdown(f"##### 📄 {t('diag.guidance', lang)}")
    with st.container(key="bot_diag"):
        st.markdown(written.text)
    speak.button(written.text, lang, key="diag_speak")

    with st.expander(f"📄 {t('ask.sources', lang)} ({len(chunks)})"):
        for i, chunk in enumerate(chunks, 1):
            st.markdown(f"**[{i}] {chunk.source}** · `{chunk.source_lang}` · "
                        f"score {chunk.score:.3f}")
            st.write(chunk.text[:400] + ("…" if len(chunk.text) > 400 else ""))


def render(lang: str, kb_count: int) -> None:
    st.caption(t("diag.hint", lang))

    chosen, snapped = st.tabs([f"🖼️ {t('diag.upload', lang)}",
                               f"📷 {t('diag.camera', lang)}"])
    with chosen:
        uploaded = st.file_uploader(t("diag.upload", lang),
                                    type=["jpg", "jpeg", "png", "webp"],
                                    label_visibility="collapsed")
    with snapped:
        # st.camera_input only offers a camera on a device that has one; on a
        # desktop it degrades to a permission prompt and then nothing, which
        # is why the upload tab is first and is the default.
        captured = st.camera_input(t("diag.camera", lang),
                                   label_visibility="collapsed")

    photo = uploaded or captured
    if photo is not None:
        st.image(photo, width=360)

    if not st.button(f"🔍 {t('diag.check', lang)}", type="primary",
                     width="stretch"):
        return

    if photo is None:
        st.warning(t("diag.nophoto", lang))
        return

    with st.spinner(t("diag.working", lang)):
        obs = crop_vision.look(photo.getvalue())

    if not obs.ok:
        st.error(obs.error)
        return

    _observation(obs, lang)
    _causes(obs, lang)

    if obs.confident_enough:
        _guidance(obs, lang, kb_count)
    else:
        # Deliberately no treatment advice below this line.
        st.warning(f"**{t('diag.unsure', lang)}**\n\n{t('diag.unsure_body', lang)}")

    st.info(f"⚠️ {t('diag.verify', lang)}")
