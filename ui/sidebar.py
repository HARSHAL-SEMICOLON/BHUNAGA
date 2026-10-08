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
from farmer import (cost_calculator, farmer_profile as profile_mod,
                    language_detector, text_embedder, vector_database)
from farmer.council import roles as council_roles
from farmer.text import t

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


def _language_picker(profile):
    """
    Outside the form and above everything else, on purpose.

    Inside the form the choice would not take effect until the farmer found and
    pressed Save — which is a lot to ask of someone who cannot read the form
    they are looking at. Here, one tap changes the whole interface immediately.
    """
    current = profile.language if profile.language in LANG_CHOICES else "auto"
    chosen = st.radio(
        "🌐 भाषा / भाषा / Language", LANG_CHOICES,
        index=LANG_CHOICES.index(current), horizontal=True,
        format_func=lambda k: LANG_LABELS[k], label_visibility="collapsed")

    if chosen != profile.language:
        profile.language = chosen
        profile_mod.save(profile)
        st.session_state["profile"] = profile
        st.rerun()
    return profile


def _profile_form(profile, lang: str):
    st.markdown(f"### 👨‍🌾 {t('side.profile', lang)}")
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

        if st.form_submit_button(t("side.save", lang), use_container_width=True):
            profile = profile_mod.Profile(
                name=name, village=village, district=district, crops=crops,
                soil=soil, land_acres=acres, language=profile.language)
            profile_mod.save(profile)
            st.session_state["profile"] = profile
            st.success(t("side.saved", lang))
    return profile


def _knowledge_base(lang: str) -> int:
    st.markdown(f"### 🌱 {t('side.kb', lang)}")
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
                 use_container_width=True):
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
        st.success(f"Loaded {total} chunks.")
        st.rerun()

    uploads = st.file_uploader(t("side.upload", lang),
                               type=["pdf", "docx", "txt", "md"],
                               accept_multiple_files=True)
    if uploads and st.button("Ingest uploaded", use_container_width=True):
        total = 0
        for upload in uploads:
            target = config.DATA_DIR / upload.name
            target.write_bytes(upload.getbuffer())
            total += _ingest_file(target)
        st.success(f"Ingested {total} chunks.")
        st.rerun()

    return count


def _settings(lang: str) -> None:
    st.markdown(f"### 🏛️ {t('side.council', lang)}")
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
        if st.button("Retry Qdrant", use_container_width=True):
            vector_database.reset()
            st.rerun()

    if not config.GROQ_API_KEY:
        st.error(t("common.nokey", lang))


def render(profile, lang: str = "en"):
    """Draw the whole sidebar. Returns (profile, chunk count)."""
    with st.sidebar:
        # the language switch comes first: everything below it is written in
        # whatever it is set to, so it has to be reachable without reading
        profile = _language_picker(profile)
        st.divider()
        profile = _profile_form(profile, lang)
        st.divider()
        count = _knowledge_base(lang)
        st.divider()
        _settings(lang)
    return profile, count
