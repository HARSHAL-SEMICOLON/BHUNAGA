# Deploying Bhunaga

The app needs these secrets (never commit them):

| Variable           | Required | Where to get it |
|--------------------|----------|-----------------|
| `GROQ_API_KEY`     | yes      | console.groq.com/keys (free) |
| `GROQ_MODEL`       | no       | defaults to `openai/gpt-oss-120b`. Groq retires models on a schedule and a retired id returns a 404, so set this when that happens |
| `VECTOR_BACKEND`   | no       | set to `local` when deploying: the index ships inside the image, so there is nothing to reach over the network |
| `QDRANT_URL`       | no       | only if you deliberately run against a live cluster |
| `QDRANT_API_KEY`   | no       | as above |
| `DATA_GOV_API_KEY` | optional | data.gov.in (only for live mandi prices; a demo key is built in) |

The embedding model **BGE-M3 (~2.3 GB)** downloads on first run and needs about
**2–3 GB RAM**. Choose a host with enough memory.

---

## Option A — Hugging Face Spaces (recommended, free, enough RAM)

Free CPU Spaces give ~16 GB RAM, which fits BGE-M3 comfortably.

1. Make a free account at huggingface.co and click **New Space**.
2. Choose **SDK: Streamlit**, name it `bhunaga`, keep it public or private.
3. Push this project to the Space's git repo. Important: the Space needs a
   `README.md` with a special header at the top — copy the file
   `deploy/HF_SPACE_README.md` to `README.md` in the Space (or merge its header
   into your README). It tells the Space to run `app.py`.
4. In **Space settings → Variables and secrets**, add `GROQ_API_KEY`,
   `QDRANT_URL`, `QDRANT_API_KEY` (and `DATA_GOV_API_KEY` if you have one).
   Spaces gives these to the app as environment variables, which `config.py`
   reads automatically.
5. Add `VECTOR_BACKEND=local` as a Variable. Deployed, there is no Qdrant
   cluster to reach and no reason to wait for one to time out.
6. The Space builds from `requirements.txt` and starts. First load is slow
   (it downloads BGE-M3 once), then it is fast.
7. Open the app and ask. The index is already in the repo (see below), so
   there is nothing to load by hand.

---

## Option B — Docker (any server / VM)

```bash
docker build -t bhunaga .
docker run -p 8501:8501 \
  -e GROQ_API_KEY=...        \
  -e QDRANT_URL=https://<cluster>.cloud.qdrant.io:6333 \
  -e QDRANT_API_KEY=...      \
  -e DATA_GOV_API_KEY=...    \
  bhunaga
```
Open http://localhost:8501. A 2 vCPU / 4 GB box is comfortable.
To avoid re-downloading BGE-M3 on restart, mount a cache:
`-v bhunaga_hf:/root/.cache/huggingface`.

---

## Option C — Streamlit Community Cloud (free, but small)

Easiest to click-deploy, BUT the free tier is memory-limited (~1 GB) and **may
crash on BGE-M3**. Two ways to make it fit:

- Use a smaller embedding model with env vars in the app's **Secrets**:
  ```toml
  EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
  EMBED_DIM = "384"
  ```
  **Read this before choosing it.** `bge-small-en-v1.5` is English-only. The
  whole claim of this project is that a Marathi question retrieves against an
  English document in one shared vector space; an English-only encoder removes
  exactly that, and the app will still appear to work while quietly answering
  Hindi and Marathi queries from near-random chunks. Never demo the trilingual
  result on this model. Re-ingest after changing it.
- Or just use Hugging Face Spaces (Option A), which has the RAM for the full
  multilingual model.

Steps: push to GitHub → share.streamlit.io → point at `app.py` → paste the same
secrets in **App settings → Secrets**.

---

## Ship the index, do not build it on the host

The index lives in `models/local_kb/` (a numpy array plus a JSON sidecar, a
couple of MB) and is committed on purpose. A free Space sleeps when idle and
comes back with a clean disk, so anything built at runtime is gone by the next
visitor: an uncommitted index means the app wakes with zero chunks and answers
nothing, while looking perfectly healthy.

Build it once locally and commit the result:

```bash
VECTOR_BACKEND=local python ingest.py --recreate   # Windows: set VECTOR_BACKEND=local
git add models/local_kb && git commit -m "Ship the prebuilt index"
```

Check it after every deploy, before anyone else does:

```bash
python check_apis.py        # prints the chunk count and which backend is live
```

Zero chunks means the index did not travel. Nothing else in the app will say so.

**Before real use**, replace the sample documents in `data/` with real ICAR/KVK
material and re-ingest. They are currently illustrative and say so in their own
first lines.
