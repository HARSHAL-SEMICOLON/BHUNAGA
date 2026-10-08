#!/usr/bin/env bash
# FARMER - one-click launcher (macOS / Linux)
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "[setup] Creating virtual environment..."
  python3 -m venv .venv
fi
PY=".venv/bin/python"

if ! "$PY" -c "import streamlit" 2>/dev/null; then
  echo "[setup] Installing dependencies (first time, ~2 GB)..."
  "$PY" -m pip install --upgrade pip
  "$PY" -m pip install -r requirements.txt
fi

[ -f .env ] || echo "[warn] .env not found. Copy .env.example to .env and add your keys."

echo "[run] Starting FARMER at http://localhost:8501"
exec "$PY" -m streamlit run app.py
