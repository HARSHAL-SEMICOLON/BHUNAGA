"""
Settings for the Bhunaga app.

We keep all the important values in one place here, like which AI models to use,
the Qdrant address, and the secret keys. If we want to change something, we
change it here once instead of in many files.

Note: Hindi and Marathi use the same letters (Devanagari). So we cannot tell
them apart just by looking. We use a small tool to find the language.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"                 # source documents (mixed-language ok)
MODELS_DIR = ROOT / "models"             # folder for saved model files
# Where the local fallback index lives. Env-readable because the ONNX backend
# needs its own index -- quantised vectors and fp32 vectors are not
# interchangeable, and searching one with the other degrades silently.
LOCAL_KB_DIR = os.getenv("LOCAL_KB_DIR", "")
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# Languages
SUPPORTED_LANGS = ("en", "hi", "mr")     # English, Hindi, Marathi
LANG_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi"}
DEFAULT_LANG = "en"                       # language we use if we are not sure

# Language ID uses lingua (pure-Python, distinguishes hi vs mr, both Devanagari).
LANGID_MIN_CONFIDENCE = 0.50              # if less sure than this, use the default language

# Embeddings (BGE-M3)
# Default is BGE-M3. On a small server you can pick a lighter model with the
# EMBED_MODEL_NAME / EMBED_DIM env vars (must match the model's vector size).
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "BAAI/bge-m3")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))   # size of the model vector
# fp16 halves memory on a GPU but is unreliable on CPU-only hosts, where some
# ops fall back or error. Env-readable so a deployment can turn it off without
# a code change. Default unchanged (True) so local behaviour is the same.
EMBED_USE_FP16 = os.getenv("EMBED_USE_FP16", "1").lower() not in ("0", "false", "no")
# Which implementation turns text into vectors.
#   "flagembedding" -> BGE-M3 through torch. ~3 GB of RAM. The default, and
#                      what the committed index was built with.
#   "onnx"          -> the same model exported to ONNX and quantised to int8.
#                      Under 1 GB, no torch, same dense + sparse outputs.
# Quantisation perturbs the vectors slightly, so an index built with one must
# be searched with the same one. ONNX_INDEX_DIR keeps them apart.
EMBED_BACKEND = os.getenv("EMBED_BACKEND", "flagembedding").strip().lower()
ONNX_REPO_ID = os.getenv("ONNX_REPO_ID", "")          # your HF model repo
ONNX_FILENAME = os.getenv("ONNX_FILENAME", "model_int8.onnx")
ONNX_LOCAL_PATH = os.getenv("ONNX_LOCAL_PATH", "")    # skips the download
# A free host gives one or two shared cores. onnxruntime defaults to one
# thread per core, and on a shared box the extra threads contend instead of
# helping, while each one costs memory we do not have.
ONNX_THREADS = int(os.getenv("ONNX_THREADS", "2"))
EMBED_BATCH_SIZE = 12
EMBED_MAX_LENGTH = 8192                   # BGE-M3 supports long context

# Qdrant (native dense + sparse)
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")          # None for local
QDRANT_COLLECTION = "farmer_kb"
QDRANT_TIMEOUT = 10                       # seconds before we give up on the cluster

# Where the vectors live.
#   "auto"   -> try Qdrant, fall back to the local store if it is unreachable
#   "qdrant" -> Qdrant only, fail loudly if it is down
#   "local"  -> always use the local store, never touch the network
# A free Qdrant Cloud cluster is switched off after a few idle weeks, so "auto"
# means a dead cluster costs you a slower search, not a dead app.
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "auto")
DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"

# Chunking
CHUNK_SIZE = 800                          # characters
CHUNK_OVERLAP = 120

# Retrieval
TOP_K = 8                                 # how many text pieces we give the AI
PREFETCH_K = 30                           # how many we pull from each search before mixing
# Give a small bonus to text in the same language as the question.
# Relative bump for evidence in the query's language: 0.10 would mean +10%,
# applied as a ratio in searcher.py because RRF scores are ~0.01-0.03 and a
# flat addition at that size is a filter rather than a tie-breaker.
#
# Default is 0, on measurement rather than principle. Across the 12-question
# set the boost never helped: Hindi keyword recall ran 0.33 additive / 0.55
# ratio / 0.60 off, Marathi 0.33 / 0.48 / 0.54, and Marathi MRR peaked with it
# off. BGE-M3's shared space already does the cross-lingual work; weighting
# toward same-language evidence only narrows what it is allowed to use.
# Set above 0 to re-enable and reproduce the comparison.
SAME_LANG_BOOST = float(os.getenv("SAME_LANG_BOOST", "0"))

# the AI that writes the answer (Groq, GPT-OSS 120B)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Key for market prices. This used to hold a literal key, which meant a working
# credential sat in a public repository -- treat that one as burned and issue a
# fresh one at data.gov.in. Set DATA_GOV_API_KEY in .env locally and in the
# host's secrets when deployed. Without it the Market screen still renders and
# labels its figures as samples, which is the designed behaviour.
_dg = (os.getenv("DATA_GOV_API_KEY") or "").strip()
DATA_GOV_API_KEY = _dg if len(_dg) >= 20 else ""   # "" not None: callers do len() on it
# Groq retired llama-3.3-70b-versatile on 2026-08-16 (404 model_not_found).
# Its documented replacement is openai/gpt-oss-120b. Env-overridable so the
# next retirement is a .env change, not a code change.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GEN_TEMPERATURE = 0.2
GEN_MAX_TOKENS = int(os.getenv("GEN_MAX_TOKENS", "2048"))

# How many finished answers to keep in memory so an identical question does not
# pay for the model twice. This matters more than it looks: with the council on,
# one question is four model calls, and the free tier allows 200,000 tokens a
# day. A jury asking the same demo question three times used to cost twelve
# calls. Set GEN_CACHE_SIZE=0 to switch it off.
GEN_CACHE_SIZE = int(os.getenv("GEN_CACHE_SIZE", "64"))

# Looking at a photograph of a sick plant. A separate model from the one that
# writes answers, because the writing model has no eyes. Env-overridable for
# the same reason as GROQ_MODEL: providers retire these without warning.
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")

# Groq bills an image at a flat 2048 input tokens and rejects requests over
# 20 MB. A phone photo is bigger than this model needs, so we shrink it before
# sending -- cheaper, faster, and it still shows a leaf spot clearly.
VISION_MAX_PIXELS = int(os.getenv("VISION_MAX_PIXELS", "1024"))
VISION_MAX_BYTES = 15 * 1024 * 1024

# Below this, we will not name a likely disease at all. A farmer who sprays on
# a 40%-confident guess has wasted the spray and possibly the crop; the honest
# output at that point is "photograph it again, closer".
VISION_MIN_CONFIDENCE = int(os.getenv("VISION_MIN_CONFIDENCE", "55"))

# gpt-oss is a reasoning model: it spends tokens thinking before it writes, and
# they come out of this same budget. At 1024 a long answer can come back empty
# -- reasoning consumed the lot -- and Devanagari is the first to suffer, since
# the same answer in Marathi costs several times the tokens it does in English.
# That failure reads as "the model is bad at Marathi" and is nothing of the
# kind. Groq's own advice is to raise the ceiling and lower the effort.
#
# 'low' also cuts the invisible reasoning spend against the 200k/day free tier,
# which is most of why a --council both run exhausts it. Values for gpt-oss are
# low | medium | high. Set empty to omit the parameter for models that reject
# it -- chat() also retries without it if the API refuses.
GROQ_REASONING_EFFORT = os.getenv("GROQ_REASONING_EFFORT", "low").strip()

# How to answer Marathi questions:
#   "native"          -> the AI writes in Marathi directly
#   "translate_after" -> the AI writes in English, then we translate to Marathi
# This only changes Marathi. Hindi and English are always written directly.
MARATHI_STRATEGY = os.getenv("MARATHI_STRATEGY", "native")  # "native" | "translate_after"
INDICTRANS2_MODEL = "ai4bharat/indictrans2-en-indic-1B"

# The council of experts (multi-agent consensus)
# Three experts read the same documents from three angles, then a chairman
# merges them. Turn it off to go back to the plain one-model answer -- keeping
# both paths is what lets us compare them in the evaluation.
COUNCIL_ENABLED = os.getenv("COUNCIL_ENABLED", "1").lower() not in ("0", "false", "no")
COUNCIL_PARALLEL = True        # ask all three at once. set False if Groq rate-limits.
COUNCIL_MIN_SPEAKERS = 1       # fewer than this and we fall back to single-agent

# Experts run a little warmer than the single-agent path. At 0.2 all three write
# almost the same sentences, and then the agreement score means nothing.
COUNCIL_MEMBER_TEMPERATURE = 0.35
COUNCIL_MEMBER_MAX_TOKENS = 600

# The chairman is the opposite: it should be dull and predictable, because it
# also has to return valid JSON.
CHAIRMAN_MODEL = os.getenv("CHAIRMAN_MODEL", GROQ_MODEL)
CHAIRMAN_TEMPERATURE = 0.1
CHAIRMAN_MAX_TOKENS = 1100

# Where the agreement score stops being "strong" and starts being a warning.
CONSENSUS_STRONG = 75          # at or above this, the experts lined up
CONSENSUS_WEAK = 45            # below this, show the farmer that they split

# Self-consistency: the control arm for the council (farmer/self_consistency.py)
#
# The council costs four calls. Comparing it against one call cannot tell you
# whether the expert roles help or whether four calls simply beat one, so the
# evaluation has a third arm that spends the same four calls on the same prompt
# repeated. Keep these two in step with the council's four calls and its member
# temperature, or the comparison stops being fair.
SELFCONS_SAMPLES = int(os.getenv("SELFCONS_SAMPLES", "4"))
SELFCONS_TEMPERATURE = COUNCIL_MEMBER_TEMPERATURE


@dataclass
class Settings:
    """Snapshot of the active config (handy for logging into eval runs)."""
    supported_langs: tuple = SUPPORTED_LANGS
    embed_model: str = EMBED_MODEL_NAME
    qdrant_collection: str = QDRANT_COLLECTION
    gen_model: str = GROQ_MODEL
    marathi_strategy: str = MARATHI_STRATEGY
    top_k: int = TOP_K
    same_lang_boost: float = SAME_LANG_BOOST
    council_enabled: bool = COUNCIL_ENABLED
    extras: dict = field(default_factory=dict)


SETTINGS = Settings()
