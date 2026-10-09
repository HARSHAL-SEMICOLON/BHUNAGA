---
title: Bhunaga
emoji: 🪱
colorFrom: green
colorTo: yellow
sdk: streamlit
sdk_version: 1.40.0
app_file: app.py
pinned: false
short_description: Trilingual (Marathi/Hindi/English) farm assistant
---

# 🪱 Bhunaga — Farmer's Best Friend

Trilingual farm assistant for Indian farmers. Ask in English, हिंदी or मराठी and
get answers from farming documents, plus weather, mandi prices and a cost
calculator.

This file is the README for the Hugging Face Space. The app code is `app.py`.
Set the secret keys in **Space settings → Variables and secrets**:

- `GROQ_API_KEY` (required)
- `VECTOR_BACKEND=local` (recommended — the index ships with the repo)
- `GROQ_MODEL` (optional — defaults to `openai/gpt-oss-120b`)
- `DATA_GOV_API_KEY` (optional — live mandi prices)
