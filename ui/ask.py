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

import html

import streamlit as st

import config
from farmer import (answer_writer, conversation, intent as intents,
                    language_detector, question_bank, searcher, text_embedder,
                    voice)
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
                     width="stretch"):
            _queue(q.text(lang))


def _topic_cards(lang: str, heading: bool = True) -> None:
    """
    Every question in the bank, grouped by topic, as tappable cards.

    This is the no-typing path. The topic name is an icon plus a word, and each
    question keeps its own icon, so the whole screen can be navigated by
    recognising pictures.
    """
    if heading:
        st.markdown(f"##### {t('ask.browse', lang)}")
    topic_names = [f"{t.icon} {t.label(lang)}" for t in question_bank.TOPICS]
    for tab, topic in zip(st.tabs(topic_names), question_bank.TOPICS):
        with tab:
            columns = st.columns(2)
            for i, q in enumerate(topic.questions):
                with columns[i % 2]:
                    # one control per question, same reasoning as the home tiles
                    with st.container(key=f"qb_{topic.key}_{i}"):
                        if st.button(f"{q.icon}  {q.text(lang)}",
                                     key=f"q_{topic.key}_{i}",
                                     width="stretch"):
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

    # "डोस किती?" means nothing on its own. If this question only makes sense
    # as a follow-up, search with the earlier subject attached and let the
    # council see what was already said. Standalone questions are untouched.
    history = conversation.from_ui_history(st.session_state.get("history"))
    search_for, conversation_context = question, ""
    if intent.needs_documents:
        search_for = history.expand(question)
        conversation_context = history.context_block(question)

    # The first question after the app wakes up pays for a 2.5 GB model
    # download before it retrieves anything. Say so, rather than showing
    # "Finding the answer..." for two minutes and looking crashed.
    if not text_embedder.is_loaded():
        spinner = t("common.firstload", lang)
    else:
        spinner = t("ask.panel" if config.COUNCIL_ENABLED else "ask.thinking",
                    lang)

    with st.spinner(spinner):
        chunks = searcher.retrieve(search_for, query_lang=lang)
        if not chunks:
            st.session_state["history"].append(
                {"q": question, "lang": lang, "council": None, "sources": [],
                 "intent": intent.name, "redirect": redirect,
                 "answer": t("ask.nothing", lang)})
            return

        profile = st.session_state.get("profile")
        context = profile.summary() if profile and profile.summary() else ""
        asked = question
        if conversation_context:
            asked = f"{conversation_context}\n\n{question}"
        if context:
            asked = f"{asked}\n\n(Farmer context: {context})"

        answer = answer_writer.generate(asked, query_lang=lang, chunks=chunks)
        st.session_state["history"].append({
            "q": question, "lang": lang, "answer": answer.text,
            "intent": intent.name, "redirect": redirect,
            "council": council_view.payload(answer.council) if answer.council else None,
            "sources": [{"source": c.source, "lang": c.source_lang,
                         "score": c.score, "text": c.text} for c in chunks],
        })


def _history(lang: str) -> None:
    """
    The conversation, oldest first.

    Reversed order was wrong: a thread that grows upwards means the answer you
    just waited for appears above the question you just typed, and following a
    follow-up means reading bottom to top. Chat reads downwards.
    """
    for i, item in enumerate(st.session_state["history"]):
        # escaped: the question is the farmer's own text, not markup
        st.markdown(f'<div class="who me">🧑\u200d🌾</div>'
                    f'<div class="msg me">{html.escape(item["q"])}</div>',
                    unsafe_allow_html=True)

        # The answer is markdown from the model — headings, lists, sometimes a
        # table. Dropping it into an HTML div renders it as literal asterisks,
        # so it goes through st.markdown inside a keyed container that the
        # stylesheet turns into the reply bubble.
        st.markdown('<div class="who">🪱 Bhunaga</div>', unsafe_allow_html=True)
        with st.container(key=f"bot{i}"):
            st.markdown(item["answer"])

        # a live-data question answered from documents is a trap; say so, and
        # offer the button that goes where the real answer is
        if item.get("redirect"):
            st.info(item["redirect"])
            screen = intents.ROUTES[item["intent"]]["screen"]
            if st.button(f"➡️ {t('nav.' + screen, lang)}", key=f"goto{i}"):
                nav.go(screen)

        # the other half of the bridge: a farmer who spoke the question can
        # hear the answer instead of being handed a screen of text
        listen, copy, _rest = st.columns([1, 1, 3])
        with listen:
            speak.button(item["answer"], item.get("lang", lang), key=f"ans{i}")
        with copy:
            # st.code carries Streamlit's own copy affordance, so the answer can
            # be lifted into WhatsApp without selecting a screenful of text
            with st.popover("📋", width="stretch"):
                st.code(item["answer"], language=None, wrap_lines=True)
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
    if kb_count <= 0:
        st.warning(t("ask.empty", lang))

    # a question queued by the mic or a card lands here on the redraw
    queued = st.session_state.pop("pending_question", "")
    if queued:
        st.session_state["question_box"] = queued

    if st.session_state["history"]:
        _history(lang)
        st.divider()

    # the composer sits below the thread, where the next thing you type goes
    box, send = st.columns([5, 1], vertical_alignment="bottom")
    with box:
        typed = st.text_input(t("ask.type", lang), key="question_box",
                              placeholder="…")
    with send:
        asked = st.button(t("ask.button", lang), type="primary",
                          width="stretch")

    _voice_row(lang)

    if typed.strip():
        _suggestions(typed, lang)

    if asked and typed.strip() and kb_count > 0:
        _answer(typed.strip(), lang, detect)
        st.rerun()

    if st.session_state["history"]:
        if st.button(f"🗑️ {t('ask.clear', lang)}"):
            st.session_state["history"] = []
            st.rerun()
        # The no-typing path used to disappear the moment a question was
        # answered, which left someone who cannot type with no second question.
        st.divider()
        with st.expander(f"👆 {t('ask.browse', lang)}"):
            _topic_cards(lang, heading=False)
    else:
        _topic_cards(lang)
