---
title: Bhunaga
emoji: 🪱
colorFrom: green
colorTo: yellow
sdk: streamlit
sdk_version: 1.58.0
app_file: app.py
pinned: false
short_description: Trilingual (Marathi/Hindi/English) farm assistant
---

# 🪱 Bhunaga — भुनागा

A trilingual farming assistant for Indian farmers. Ask in **English, हिंदी or
मराठी** — by speaking, tapping a question, or typing — and get an answer in the
same language, grounded in agricultural documents rather than guessed.

Also on board: a 7-day forecast, a spraying window computed from hourly wind
and rain, soil data for your village, mandi prices, and a cost calculator.

## Setting it up

Add these under **Settings → Variables and secrets**:

| Name | Required | What it does |
|---|---|---|
| `GROQ_API_KEY` | **yes** | answers, the expert council, and voice transcription |
| `VECTOR_BACKEND` | recommended | set to `local` — the search index ships inside the repo |
| `GROQ_MODEL` | no | defaults to `openai/gpt-oss-120b` |
| `DATA_GOV_API_KEY` | no | live mandi prices; without it the Market screen clearly labels its figures as samples |

Without `GROQ_API_KEY` the Space still starts and every screen renders — the
answer and voice features simply report that the key is missing. That is
deliberate: a half-configured deployment should say what is wrong, not crash.

## Two things to expect

**The first question is slow.** BGE-M3, the multilingual embedding model, is
about 2.5 GB and downloads on first use. After that it is cached and fast.

**The search index is committed to the repo** (`models/local_kb/`). A Space has
no build step and its disk is wiped when it sleeps, so an index built at deploy
time would vanish. Shipping it means the Space wakes up able to answer. Rebuild
it with `python ingest.py --recreate` after changing anything in `data/`.

## Source

Code, documentation and the evaluation harness:
<https://github.com/HARSHAL-SEMICOLON/BHUNAGA>
