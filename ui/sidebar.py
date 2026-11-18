"""
The side panel: the farmer's details, the knowledge base, and the settings.

This is the one part of the app aimed at whoever set the thing up rather than at
the farmer, so it is allowed to use words like "chunks" and "Qdrant".

It is also where the knowledge base tells you the truth about itself: how many
chunks are indexed, which backend they are in, and — if we fell back to the
local store — one plain line saying why.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import streamlit as st

import config
import ingest as ingest_mod
from farmer import (answer_writer, cost_calculator,
                    farmer_profile as profile_mod,
                    language_detector, text_embedder, vector_database)
from farmer.council import roles as council_roles
from farmer.text import t
from ui import nav, theme

LANG_CHOICES = ["auto", "en", "hi", "mr"]
LANG_LABELS = {"auto": "🌐 Auto", "en": "English", "hi": "हिंदी", "mr": "मराठी"}


def _ingest_file(path: Path, rebuild: bool = False) -> int:
    """
    Read one file, chunk it, embed it, save it. Returns the chunk count.

    `rebuild` drops the whole collection first. The sample knowledge base is a
    fixed, known set of documents, so loading it twice should give the same
    index, not two copies of it — upserting with fresh UUIDs would otherwise
    duplicate every chunk and quietly skew retrieval towards whatever was
    loaded most often.
    """
    text = ingest_mod.load_text(path)
    chunks = ingest_mod.chunk_text(text)
    if not chunks:
        return 0

    embeddings = text_embedder.embed_texts(chunks)
    client = vector_database.get_client()
    vector_database.ensure_collection(client, recreate=rebuild)
    points = [
        vector_database.build_point(
            point_id=str(uuid.uuid4()), dense=e.dense, sparse=e.sparse,
            payload={"text": chunk, "source": path.name,
                     "source_lang": language_detector.detect(chunk).lang})
        for chunk, e in zip(chunks, embeddings)
    ]
    client.upsert(collection_name=config.QDRANT_COLLECTION, points=points)
    return len(points)


# both copies of the switch, so each can be kept in step with the other
PICKER_KEYS = ("lang_side",)


def _language_changed(key: str) -> None:
    """
    One switch was tapped; make that the truth everywhere.

    This has to be a callback rather than a plain read-after-render. A
    Streamlit widget that owns a `key` takes its value from session state, not
    from the `index` you pass it — so with two pickers on screen, whichever
    drew second would re-assert its own stale value and silently undo the tap
    on the other one. That is exactly what happened: the sidebar always won and
    the switch above the navigation did nothing at all.

    Running on change, before the rerun, means the new choice is written to the
    profile and to BOTH widgets while there is still only one answer in play.
    """
    chosen = st.session_state.get(key)
    if chosen not in LANG_CHOICES:
        return

    profile = st.session_state.get("profile")
    if profile is None or chosen == profile.language:
        return

    profile.language = chosen
    profile_mod.save(profile)
    st.session_state["profile"] = profile
    for other in PICKER_KEYS:
        st.session_state[other] = chosen


def _language_picker(profile, key: str = "lang_side"):
    """
    Outside the form and above everything else, on purpose.

    Inside the form the choice would not take effect until the farmer found and
    pressed Save — which is a lot to ask of someone who cannot read the form
    they are looking at. Here, one tap changes the whole interface immediately.
    """
    # seed once; after that the widget owns its own state and `index` would be
    # ignored anyway, so passing it would only be misleading
    if key not in st.session_state:
        st.session_state[key] = (profile.language
                                 if profile.language in LANG_CHOICES else "auto")

    st.radio(
        "🌐 भाषा / भाषा / Language", LANG_CHOICES, horizontal=True, key=key,
        on_change=_language_changed, args=(key,),
        format_func=lambda k: LANG_LABELS[k], label_visibility="collapsed")

    return st.session_state.get("profile", profile)



def _profile_form(profile, lang: str):
    with st.form("profile_form"):
        name = st.text_input(t("side.name", lang), profile.name)
        village = st.text_input(t("side.village", lang), profile.village)
        district = st.text_input(t("side.district", lang), profile.district)
        crops = st.multiselect(
            t("side.crops", lang), list(cost_calculator.CROP_DEFAULTS.keys()),
            default=[c for c in profile.crops if c in cost_calculator.CROP_DEFAULTS])
        soil = st.selectbox(
            t("side.soil", lang), profile_mod.SOIL_TYPES,
            index=profile_mod.SOIL_TYPES.index(profile.soil)
            if profile.soil in profile_mod.SOIL_TYPES else 0)
        acres = st.number_input(t("side.land", lang), 0.0, 10000.0,
                                float(profile.land_acres), step=0.5)

        if st.form_submit_button(t("side.save", lang), width="stretch"):
            profile = profile_mod.Profile(
                name=name, village=village, district=district, crops=crops,
                soil=soil, land_acres=acres, language=profile.language)
            profile_mod.save(profile)
            st.session_state["profile"] = profile
            st.success(t("side.saved", lang))
    return profile


def _knowledge_base(lang: str) -> int:
    client = vector_database.get_client()
    count = vector_database.count(client)
    backend = vector_database.backend()

    if backend == "local":
        st.info("📁 Using the local store on this computer.")
        if vector_database.why_local():
            st.caption(f"Qdrant was not used: {vector_database.why_local()}")
    else:
        st.caption("☁️ Connected to Qdrant.")

    if count > 0:
        st.success(f"{count} {t('side.chunks', lang)}")
    elif count == 0:
        st.warning(t("side.kb_empty", lang))
    else:
        st.error("Could not read the store.")

    samples = (sorted(config.DATA_DIR.glob("*.md"))
               + sorted(config.DATA_DIR.glob("*.txt")))
    if st.button(f"{t('side.load', lang)} ({len(samples)})",
                 width="stretch"):
        progress = st.progress(0.0)
        total = 0
        for i, path in enumerate(samples, 1):
            try:
                # only the first file rebuilds; the rest add to it
                total += _ingest_file(path, rebuild=(i == 1))
            except Exception as exc:
                st.error(f"{path.name}: {str(exc)[:160]}")
                break
            progress.progress(i / max(len(samples), 1))
        # the corpus just changed, so answers written from the old one are
        # no longer the best available. the cache key includes the retrieved
        # text and would miss anyway, but holding them wastes memory.
        answer_writer.clear_cache()
        st.success(f"Loaded {total} chunks.")
        st.rerun()

    uploads = st.file_uploader(t("side.upload", lang),
                               type=["pdf", "docx", "txt", "md"],
                               accept_multiple_files=True)
    if uploads and st.button("Ingest uploaded", width="stretch"):
        total = 0
        for upload in uploads:
            target = config.DATA_DIR / upload.name
            target.write_bytes(upload.getbuffer())
            total += _ingest_file(target)
        st.success(f"Ingested {total} chunks.")
        st.rerun()

    return count


def _settings(lang: str) -> None:
    config.COUNCIL_ENABLED = st.toggle(
        t("side.council_on", lang), value=config.COUNCIL_ENABLED,
        help="A crop expert, a money expert and a schemes expert each read the "
             "same documents, then a chairman merges what they say and scores "
             "how much they agreed. Slower, but you can see the disagreements.")
    if config.COUNCIL_ENABLED:
        st.caption(" · ".join(f"{s.icon} {s.title}"
                              for s in council_roles.SEATS))
    else:
        st.caption("Single-model answers — faster, no second opinion.")

    with st.expander(t("side.advanced", lang)):
        config.MARATHI_STRATEGY = st.radio(
            "Marathi strategy", ["native", "translate_after"],
            index=0 if config.MARATHI_STRATEGY == "native" else 1)
        config.TOP_K = st.slider("Chunks retrieved", 1, 15, config.TOP_K)
        config.COUNCIL_PARALLEL = st.checkbox(
            "Ask the experts in parallel", value=config.COUNCIL_PARALLEL,
            help="Uncheck if the Groq free tier starts rate-limiting you.")
        if st.button("Retry Qdrant", width="stretch"):
            vector_database.reset()
            st.rerun()

    if not config.GROQ_API_KEY:
        st.error(t("common.nokey", lang))


def status_pills(count: int, lang: str) -> list[tuple[str, str]]:
    """
    What is actually working right now, for the bar across the top.

    Three things decide whether an answer can happen at all: a model key, an
    index with something in it, and which store that index is in. Showing them
    beats a farmer -- or a reviewer -- discovering the failure mid-question.
    """
    pills: list[tuple[str, str]] = []

    if config.GROQ_API_KEY:
        pills.append(("ok", config.GROQ_MODEL.split("/")[-1]))
    else:
        pills.append(("off", "no model key"))

    if count > 0:
        pills.append(("ok", f"{count} {t('side.chunks', lang)}"))
    else:
        pills.append(("off", t("side.kb_empty", lang)))

    backend = vector_database.backend()
    # Qdrant is a product name and stays; the fallback is a thing a person
    # reads, so it gets translated like everything else.
    pills.append(("ok", "Qdrant") if backend != "local"
                 else ("warn", t("side.local", lang)))
    return pills


def render(profile, lang: str = "en"):
    """
    Draw the whole sidebar. Returns (profile, chunk count).

    Order matters. Navigation first, because that is what it is mostly used
    for. Then the language switch, because everything below it is written in
    whatever it is set to, so it has to be reachable without reading. Then the
    farmer's own details. The operator controls -- the index, the council, the
    retrieval knobs -- go last and start folded away: they use words like
    "chunks" and nobody standing in a field needs them.
    """
    with st.sidebar:
        theme.brand()
        nav.sidebar_nav(lang)

        theme.group(t("side.language", lang))
        profile = _language_picker(profile)

        theme.group(t("side.setup", lang))
        with st.expander(f"👨‍🌾 {t('side.profile', lang)}"):
            profile = _profile_form(profile, lang)
        with st.expander(f"🌱 {t('side.kb', lang)}"):
            count = _knowledge_base(lang)
        with st.expander(f"🏛️ {t('side.council', lang)}"):
            _settings(lang)

        # what is actually working, at the foot of the panel rather than
        # floating over the page
        theme.group(t("side.status", lang))
        st.markdown(
            "".join(f'<span class="pill {state}"><span class="dot"></span>'
                    f'{label}</span> '
                    for state, label in status_pills(count, lang)),
            unsafe_allow_html=True)
    return profile, count
