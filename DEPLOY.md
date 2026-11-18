# Deploying Bhunaga

**Target: Streamlit Community Cloud, free, no credit card.**

The route this file used to describe — Hugging Face Spaces on the free
Streamlit SDK — no longer exists. Two separate changes closed it:

- Hugging Face **deprecated the Streamlit SDK**. Their docs now say to pick the
  Docker SDK and use the Streamlit template instead.
- **Docker Spaces require a paid plan** (PRO, $9/month for a personal account).
  Only static HTML Spaces are still free.

Streamlit Community Cloud is free and needs no card, but it gives an app
**between 690 MB and 2.7 GB of RAM**, and BGE-M3 under FlagEmbedding needs
about 3 GB. So the model has to get smaller before the app can go live for
nothing. That is what `scripts/build_onnx_embedder.py` is for.

---

## How the free deployment works

The same BGE-M3, exported to ONNX and quantised to int8:

| | FlagEmbedding (local dev) | ONNX int8 (deployed) |
|---|---|---|
| Weights | ~2.2 GB | ~0.6 GB |
| Runtime RAM | ~3 GB | under 1 GB |
| Needs torch | yes | no |
| Dense + sparse | yes | yes |
| Index it matches | `models/local_kb/` | `models/local_kb_onnx/` |

Both paths live in `farmer/text_embedder.py` and are chosen by
`EMBED_BACKEND`. The default is `flagembedding`, so **local development is
unchanged** — you only get the ONNX path if you ask for it.

### Why there are two indexes

Quantisation moves the vectors slightly. A query embedded by the int8 model
searched against an index built by the fp32 model still returns results, just
worse ones — there is no error, no warning, nothing in the logs. The only
symptom is that answers get vaguer. Keeping the indexes apart under
`LOCAL_KB_DIR` makes the mismatch impossible rather than merely unlikely.

---

## Step 0 — check nothing is broken

```cmd
cd /d "E:\RESUME PROJECTS\FARMER"
.venv\Scripts\activate.bat
pip install pytest
python -m pytest tests/ -q
```

`pytest` is not in `requirements.txt` — it is a dev-only dependency, so a fresh
virtual environment will not have it. Use `python -m pytest`, not `pytest`:
the bare command depends on the venv's Scripts folder being on PATH, and often
it is not.

## Step 1 — build the quantised model

About 30 minutes, nearly all of it download.

```cmd
pip install onnxruntime transformers huggingface-hub
python scripts\build_onnx_embedder.py
```

This downloads the fp32 ONNX export (2.2 GB), quantises it to int8 (~0.6 GB),
and then **compares the two on six probe questions across all three
languages**. It stops with an error if agreement is poor:

| Measure | Hard stop below | Advisory below |
|---|---|---|
| dense cosine, worst probe | 0.95 | 0.99 |
| sparse weight overlap, worst probe | 0.90 | — |

The dense check used to hard-stop at 0.99. That was the wrong number: it
compares an int8 query against an fp32 index, but deployment embeds the index
with int8 too, so most of that difference is common-mode and cancels out in the
ranking. Between 0.95 and 0.99 the script now warns and continues. Step 2 is
what actually decides, because it measures retrieval rather than vector
similarity.

## Step 2 — rebuild the index to match, and prove it did not regress

Keep the same terminal window: `set` only lasts for that session.

```cmd
set EMBED_BACKEND=onnx
set ONNX_LOCAL_PATH=E:\RESUME PROJECTS\FARMER\models\onnx\model_int8.onnx
set LOCAL_KB_DIR=models/local_kb_onnx
set VECTOR_BACKEND=local
python ingest.py --recreate
python evaluate.py
```

Compare against the known baseline for the no-boost condition:

| | baseline |
|---|---|
| Hindi keyword recall | 0.60 |
| Marathi keyword recall | 0.54 |
| MRR | 0.81 |

A point or two down is quantisation noise. A large drop means stop and
investigate rather than ship.

### Rebuild the fp32 index too

`models/local_kb/` was built before the duplicate-chunk fix and still holds 480
chunks, of which 114 are exact duplicates; the ONNX index holds the correct 366.
That makes local development disagree with the deployed app and with the report.
Fix it in a **separate terminal**, so the ONNX environment variables above are
not in scope:

```cmd
cd /d "E:\RESUME PROJECTS\FARMER"
.venv\Scripts\activate.bat
set VECTOR_BACKEND=local
python ingest.py --recreate
```

`--recreate` is the whole point: without it `ingest.py` appends, which is how
the duplicates arrived.

## Step 3 — host the model file

The quantised model is ~600 MB, far past GitHub's 100 MB per-file limit, so it
goes in a Hugging Face **model repo** — those are still free, it is only Spaces
that now need PRO. The app downloads it once on first run and then reads it
from cache.

```cmd
hf auth login
hf repo create bge-m3-int8 --repo-type model
hf upload ZEUSxHARSHAL/bge-m3-int8 models\onnx\model_int8.onnx model_int8.onnx
```

`huggingface-cli` was renamed to `hf` and the old name now refuses to run. The
arguments are unchanged: repo id, local file, name inside the repo.

The token `hf auth login` asks for needs **write** permission. The token the
website offers by default is read-only, and a read token fails only at the end
of the upload.

`hf upload` would create the repo on its own, but the docs do not say whether
it comes out public or private. The app downloads this file anonymously, so it
must be public — hence creating it explicitly first, where public is the
default.

## Step 4 — push

```cmd
git add -A
git add -f models/local_kb_onnx/dense.npy models/local_kb_onnx/meta.json
git commit -m "ONNX int8 embedder for free-tier deployment"
git push origin main
```

`models/onnx/` is gitignored — those are the big intermediates.
`models/local_kb_onnx/` is committed on purpose: it is a few MB, and a deployed
app has no build step, so an index built at deploy time would vanish on the
next sleep and the app would wake up answering nothing.

## Step 5 — deploy

[share.streamlit.io](https://share.streamlit.io) → **New app** →
repo `HARSHAL-SEMICOLON/BHUNAGA`, branch `main`, file `app.py`.

Then **Settings → Secrets**:

```toml
GROQ_API_KEY = "..."
DATA_GOV_API_KEY = "..."
EMBED_BACKEND = "onnx"
ONNX_REPO_ID = "ZEUSxHARSHAL/bge-m3-int8"
LOCAL_KB_DIR = "models/local_kb_onnx"
VECTOR_BACKEND = "local"
```

The two namespaces are different and both are right: the GitHub repo is
`HARSHAL-SEMICOLON/BHUNAGA`, the Hugging Face account is `ZEUSxHARSHAL`.

`VECTOR_BACKEND=local` matters. Without it the app tries Qdrant first, waits
out the timeout and only then falls back — a slow first load for no benefit,
since the index ships in the repo.

---

## Five defects fixed before the first deploy

All five were invisible locally and would only have failed once deployed.

1. **`requirements.txt` pulled the CUDA build of torch.** FlagEmbedding brings
   torch in as a dependency, and PyPI's default Linux wheel is the CUDA one —
   about 2.5 GB, which times out or fills the disk on a free host. The
   `--extra-index-url` line at the top makes pip prefer the CPU wheel. It has
   to stay at the top: pip reads index options before any requirement.

2. **The Docker healthcheck could never pass.** It called `curl`, and
   `python:3.11-slim` ships no curl. The check failed for ever and some
   platforms restart-loop a container that never reports healthy. It now uses
   `python -c` instead, so nothing extra needs installing.

3. **`EMBED_USE_FP16` was hardcoded to `True`.** fp16 is unreliable on CPU-only
   hosts, where some operations fall back or error outright. It is now read
   from the environment, default unchanged.

4. **`deploy/HF_SPACE_README.md` declared `sdk: streamlit`,** which Hugging
   Face has deprecated.

5. **A live data.gov API key was hardcoded in `config.py`** and committed to a
   public repository. It is removed. **Treat that key as burned and issue a
   fresh one** at data.gov.in. Without a key the Market screen still renders
   and labels its figures as samples, which is the designed behaviour.

---

## What to expect once deployed

**The first question is slow.** The model downloads on first use. The app says
so explicitly — "Getting ready — this only happens the first time" — rather
than showing a generic spinner that reads like a crash.

**A sleeping app loses the cache.** After a long idle period the first question
pays the download again. The index does not need rebuilding; it is in the repo.

**Without `DATA_GOV_API_KEY` the Market screen shows sample prices**, in a red
box reading "NOT today's rates". That is deliberate — a farmer acting on a
placeholder price loses real money, so it is loud rather than subtle.

---

## If something goes wrong

Run the diagnostic first. It checks all six external services and says which
one is broken and why:

```cmd
python check_apis.py --raw
```

| Symptom | Cause |
|---|---|
| `No module named pytest` | dev dependency; `pip install pytest` |
| Build times out on Streamlit Cloud | comment out `FlagEmbedding` in `requirements.txt` on a deploy branch — the ONNX path never imports it, so torch is dead weight in production |
| App crashes with a memory error | `EMBED_BACKEND` is not set to `onnx`, so it loaded the 3 GB model |
| Answers are vague but nothing errors | `LOCAL_KB_DIR` is pointing at the fp32 index while the ONNX backend is active — the mismatch described above |
| Every answer says the knowledge base is empty | `models/local_kb_onnx/` did not get committed, or `VECTOR_BACKEND` is not `local` |
| Answers fail, screens fine | `GROQ_API_KEY` missing or the model id retired — check the logs |
| `TypeError` about `width` or `key` on first load | Streamlit older than 1.50 |
| Market shows red sample prices | expected without `DATA_GOV_API_KEY` |

---

## Option B — Docker, on any server

`Dockerfile` is current and takes its secrets from the environment.

```bash
docker build -t bhunaga .
docker run -p 8501:8501 \
  -e GROQ_API_KEY=...        \
  -e VECTOR_BACKEND=local    \
  -e DATA_GOV_API_KEY=...    \
  bhunaga
```

A 2 vCPU / 4 GB box runs the FlagEmbedding path comfortably, so no ONNX
conversion is needed. Mount a volume at `/root/.cache/huggingface` so a restart
does not re-download the model.

This is also the route for Hugging Face Spaces if you ever take a PRO plan, and
for Google Cloud Run, whose free tier does allow 4 GB of RAM but requires a
card on file.

## Option C — the phone channels

WhatsApp and IVR run as a separate service from the web app, and need a public
HTTPS URL plus a Twilio account. **Built but never tested against a live
provider** — make no claims for them until they are.

```bash
pip install fastapi uvicorn
python channels/webhook.py
```
