@echo off
REM ============================================================
REM  FARMER - one-click launcher (Windows)
REM  Creates the virtual env (first run), installs deps, starts app
REM ============================================================
setlocal
cd /d "%~dp0"

REM 1. Create venv on first run
if not exist ".venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment...
    py -m venv .venv
    if errorlevel 1 python -m venv .venv
)

set "PY=.venv\Scripts\python.exe"

REM 2. Install dependencies if streamlit is missing
"%PY%" -c "import streamlit" 2>nul
if errorlevel 1 (
    echo [setup] Installing dependencies ^(first time, ~2 GB, please wait^)...
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install -r requirements.txt
)

REM 3. Check for .env
if not exist ".env" (
    echo [warn] .env not found. Copy .env.example to .env and add your keys.
)

REM 4. Launch
echo [run] Starting FARMER at http://localhost:8501
"%PY%" -m streamlit run app.py

endlocal
