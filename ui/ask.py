"""
The Ask screen.

Three ways in, on purpose, because farmers are not one kind of person:

  🎤 speak it     for someone who cannot read or write at all
  👆 tap a card   for someone who reads a little but will not type Devanagari
  ⌨️ type it      for someone comfortable with a keyboard, with suggestions
                  appearing as they go

They all end up in the same place: text in the box, then the same retrieve →
council → answer path.

The one thing to know about the code: Streamlit will not let you write to a
widget's state after that widget exists, so voice and the tap cards put their
text into a separate pending slot and call st.rerun(). The box picks it up on
the way back. Trying to set it directly throws StreamlitAPIException.
"""

from __future__ import annotations

import streamlit as st

import config
from farmer import (answer_writer, intent as intents, language_detector,
                    question_bank, searcher, voice)
from farmer.text import t
from ui import council_view, nav, speak


def _queue(text: str) -> None:
    """Put a question in the box and redraw. See the note in the docstring."""
    st.session_state["pending_question"] = text
    st.rerun()


def _voice_row(lang: str) -> None:
    """Record, transcribe, drop the text in the box."""
    recording = st.audio_input(t("ask.speak", lang), key="voice_clip")
    if not recording:
        return

    # the same clip stays in the widget after a rerun, so remember what we have
    # already sent up. otherwise every redraw pays for another transcription.
    clip = recording.getvalue()
    if st.session_state.get("voice_done") == len(clip):
        return

    with st.spinner(t("ask.listening", lang)):
        heard = voice.transcribe(clip, lang_hint=lang if lang != "auto" else "")
    st.session_state["voice_done"] = len(clip)

    if heard.ok:
        _queue(heard.text)
    else:
        st.warning(heard.error)


def _suggestions(typed: str, lang: str) -> None:
    """Matching questions, as buttons. Shown while the farmer types."""
    matches = question_bank.suggest(typed, lang, limit=4)
    if not matches:
        return
    for i, q in enumerate(matches):
        if st.button(f"{q.icon}  {q.text(lang)}", key=f"sugg_{i}",
                     use_container_width=True):
            _queue(q.text(lang))


def _topic_cards(lang: str) -> None:
    """
    Every question in the bank, grouped by topic, as tappable cards.

    This is the no-typing path. The topic name is an icon plus a word, and each
    question keeps its own icon, so the whole screen can be navigated by
    recognising pictures.
    """
    st.markdown(f"##### {t('ask.browse', lang)}")
    topic_names = [f"{t.icon} {t.label(lang)}" for t in question_bank.TOPICS]
    for tab, topic in zip(st.tabs(topic_names), question_bank.TOPICS):
        with tab:
            columns = st.columns(2)
            for i, q in enumerate(topic.questions):
                with columns[i % 2]:
                    st.markdown(
                        f'<div class="qcard"><span class="ic">{q.icon}</span> '
                        f'<span class="tx">{q.text(lang)}</span></div>',
                        unsafe_allow_html=True)
                    if st.button("👆", key=f"q_{topic.key}_{i}",
                                 use_container_width=True):
                        _queue(q.text(lang))


def _answer(question: str, lang: str, detect: bool) -> None:
    """
    Retrieve, ask the council, and remember the result.

    `detect` is on when the farmer left the language on "auto". We work it out
    from the question itself rather than the interface language, because plenty
    of people read the English interface and then ask in Marathi.
    """
    if detect:
        lang = language_detector.detect(question).lang

    # Some questions cannot be answered from documents at all. "What is onion
    # selling for today?" needs the live feed; retrieving a storage guide and
    # writing a confident paragraph from it would be worse than saying so.
    intent = intents.classify(question)
    redirect = intents.redirect_note(intent, lang) if not intent.needs_documents else ""

    spinner = t("ask.panel" if config.COUNCIL_ENABLED else "ask.thinking", lang)
    with st.spinner(spinner):
        chunks = searcher.retrieve(question, query_lang=lang)
        if not chunks:
            st.session_state["history"].append(
                {"q": question, "lang": lang, "council": None, "sources": [],
                 "intent": intent.name, "redirect": redirect,
                 "answer": t("ask.nothing", lang)})
            return

        profile = st.session_state.get("profile")
        context = profile.summary() if profile and profile.summary() else ""
        asked = question + (f"\n\n(Farmer context: {context})" if context else "")

        answer = answer_writer.generate(asked, query_lang=lang, chunks=chunks)
        st.session_state["history"].append({
            "q": question, "lang": lang, "answer": answer.text,
            "intent": intent.name, "redirect": redirect,
            "council": council_view.payload(answer.council) if answer.council else None,
            "sources": [{"source": c.source, "lang": c.source_lang,
                         "score": c.score, "text": c.text} for c in chunks],
        })


def _history(lang: str) -> None:
    for i, item in enumerate(reversed(st.session_state["history"])):
        st.markdown(f'<div class="asked">🧑‍🌾 {item["q"]}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="card">{item["answer"]}</div>',
                    unsafe_allow_html=True)

        # a live-data question answered from documents is a trap; say so, and
        # offer the button that goes where the real answer is
        if item.get("redirect"):
            st.info(item["redirect"])
            screen = intents.ROUTES[item["intent"]]["screen"]
            if st.button(f"➡️ {t('nav.' + screen, lang)}", key=f"goto{i}"):
                nav.go(screen)

        # the other half of the bridge: a farmer who spoke the question can
        # hear the answer instead of being handed a screen of text
        speak.button(item["answer"], item.get("lang", lang), key=f"ans{i}")
        if item.get("council"):
            council_view.render(item["council"], lang)
        if item["sources"]:
            with st.expander(f"📄 {t('ask.sources', lang)} "
                             f"({len(item['sources'])})"):
                for i, s in enumerate(item["sources"], 1):
                    st.markdown(f"**[{i}] {s['source']}** · `{s['lang']}` · "
                                f"score {s['score']:.3f}")
                    st.write(s["text"][:400] + ("…" if len(s["text"]) > 400 else ""))


def render(lang: str, kb_count: int, detect: bool = True) -> None:
    """
    Draw the whole screen.

    `lang` is the interface language and is never "auto" — app.py resolves that
    before we get here. `detect` says whether to work the answer language out
    from each question instead of using `lang`.
    """
    st.markdown(f"### {t('ask.head', lang)}")
    st.caption("English · हिंदी · मराठी")

    if kb_count <= 0:
        st.warning(t("ask.empty", lang))

    left, right = st.columns([1, 1])
    with left:
        _voice_row(lang)

    # a question queued by the mic or a card lands here on the redraw
    queued = st.session_state.pop("pending_question", "")
    if queued:
        st.session_state["question_box"] = queued

    with right:
        typed = st.text_input(t("ask.type", lang), key="question_box",
                              placeholder="…")

    if typed.strip():
        _suggestions(typed, lang)

    asked = st.button(t("ask.button", lang), type="primary",
                      use_container_width=True)
    if asked and typed.strip() and kb_count > 0:
        _answer(typed.strip(), lang, detect)

    if st.session_state["history"]:
        if st.button(t("ask.clear", lang)):
            st.session_state["history"] = []
            st.rerun()
        _history(lang)
    else:
        _topic_cards(lang)
