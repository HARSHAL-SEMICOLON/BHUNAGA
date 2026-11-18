@echo off
rem ===================================================================
rem  Does int8 quantisation hurt retrieval?
rem
rem  Runs the same 36 eval rows twice -- once with the int8 ONNX embedder,
rem  once with fp32 FlagEmbedding -- over the same 366-chunk corpus, so the
rem  embedder is the only thing that differs.
rem
rem  --fresh      ignore saved rows. Without it the script finds 36 rows
rem               "already done" and reports an older index's numbers while
rem               evaluating nothing.
rem  --no-generate  retrieval metrics only. Quantisation can only affect
rem               hit@k, kw_rec, MRR and same_lg, all of which are pure
rem               retrieval. Generating answers would cost ~36 x 4 council
rem               calls against a 200k/day budget and measure nothing.
rem ===================================================================
setlocal
cd /d "%~dp0.."
call .venv\Scripts\activate.bat

echo.
echo === clearing stale bytecode ===
rem Python normally invalidates .pyc by mtime, but a file written by a tool
rem can land with an older mtime than its cached bytecode, and then an edit
rem silently does nothing.
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul

set VECTOR_BACKEND=local

echo.
echo ============================================================
echo  ARM 1 of 2   int8 ONNX    (index already built)
echo ============================================================
set EMBED_BACKEND=onnx
set ONNX_LOCAL_PATH=%CD%\models\onnx\model_int8.onnx
set LOCAL_KB_DIR=models/local_kb_onnx
python evaluate.py --fresh --no-generate --out eval/results_onnx
if errorlevel 1 goto fail

echo.
echo ============================================================
echo  ARM 2 of 2   fp32 FlagEmbedding    (building clean index)
echo ============================================================
set EMBED_BACKEND=flagembedding
set ONNX_LOCAL_PATH=
set LOCAL_KB_DIR=models/local_kb_clean
python ingest.py --recreate
if errorlevel 1 goto fail
python evaluate.py --fresh --no-generate --out eval/results_fp32
if errorlevel 1 goto fail

echo.
echo ============================================================
echo  Done. Send both tables above.
echo
echo  Re-read either later without re-running:
echo    python evaluate.py --report --out eval/results_onnx
echo    python evaluate.py --report --out eval/results_fp32
echo ============================================================
goto end

:fail
echo.
echo ============================================================
echo  FAILED above. Send the error -- do not continue.
echo ============================================================
exit /b 1

:end
endlocal
