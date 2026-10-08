# Deploying Bhunaga

The app needs these secrets (never commit them):

| Variable           | Required | Where to get it |
|--------------------|----------|-----------------|
| `GROQ_API_KEY`     | yes      | console.groq.com/keys (free) |
| `QDRANT_URL`       | yes      | your Qdrant Cloud cluster endpoint (ends in `:6333`) |
| `QDRANT_API_KEY`   | yes      | Qdrant Cloud |
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
5. The Space builds from `requirements.txt` and starts. First load is slow
   (it downloads BGE-M3 once), then it is fast.
6. Open the app → sidebar → **Load sample KB** → start asking.

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
  (Note: small English models lose some Marathi/Hindi quality — fine for a demo,
  not ideal for real trilingual use. Re-ingest after changing the model.)
- Or just use Hugging Face Spaces (Option A), which has the RAM for the full
  multilingual model.

Steps: push to GitHub → share.streamlit.io → point at `app.py` → paste the same
secrets in **App settings → Secrets**.

---

## First run after deploy
Open the app → sidebar → **Load sample KB** to fill Qdrant, then use the tabs.
Replace the sample documents with real ICAR/KVK material before real use.
