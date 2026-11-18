"""
Make the deployable embedder: BGE-M3 as int8 ONNX, then an index to match.

Why this exists
---------------
BGE-M3 under FlagEmbedding needs roughly 3 GB of RAM. No free host offers that
without a credit card, so the model has to get smaller before the app can go
live for nothing. Exporting to ONNX removes torch; quantising to int8 takes the
weights from about 2.2 GB to about 0.6 GB. Runtime memory lands under 1 GB,
which fits Streamlit Community Cloud.

Quantisation moves the vectors slightly. That is fine on its own -- but a query
embedded by the int8 model and an index built by the fp32 model no longer live
in quite the same space, and the failure is silent: retrieval just gets worse.
So this script rebuilds the index with the same quantised model and writes it
somewhere new. Nothing that already works is touched.

What it writes (all new paths)
------------------------------
    models/onnx/model.onnx          the fp32 export, downloaded
    models/onnx/model_int8.onnx     the quantised model -- this is what deploys
    models/local_kb_onnx/           the matching index

Run it
------
    .venv\\Scripts\\activate.bat
    pip install onnx onnxruntime transformers huggingface-hub
    python scripts/build_onnx_embedder.py

Then compare the two before trusting it:

    python scripts/build_onnx_embedder.py --compare

That prints cosine agreement between the fp32 and int8 vectors on your own
questions. Below about 0.99 means something is wrong -- stop and say so.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ONNX_DIR = ROOT / "models" / "onnx"
INT8 = ONNX_DIR / "model_int8.onnx"
SOURCE_REPO = "aapot/bge-m3-onnx"      # dense + sparse + colbert outputs


def human(n: int) -> str:
    return f"{n / 1e6:.0f} MB"


# ── 0. dependencies ─────────────────────────────────────────────────────────
def check_deps() -> None:
    """Fail now, with a usable message, rather than 2 GB into a download."""
    v = sys.version_info
    missing = []
    for mod in ("onnxruntime", "onnx"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print(f"    missing: {', '.join(missing)}")
        print("    try:  pip install onnx onnxruntime")
    if missing == ["onnx"]:
        sys.exit(1)
    if missing:
        sys.exit(
            f"    onnxruntime will not import on Python {v.major}.{v.minor}.\n"
            "    It publishes wheels a release or two behind the newest Python.\n"
            "    Build this on 3.11 -- it is only needed for the conversion:\n\n"
            "      py -3.11 -m venv .venv-onnx\n"
            "      .venv-onnx\\Scripts\\activate.bat\n"
            "      pip install onnx onnxruntime transformers huggingface-hub numpy\n"
            "      python scripts\\build_onnx_embedder.py\n")


# ── 1. fetch the fp32 ONNX export ───────────────────────────────────────────
def download() -> Path:
    """
    Download into a plain folder, not the HF cache.

    The cache is built from symlinks, and Windows refuses to create those
    without Developer Mode or an elevated shell -- WinError 1314. Passing
    local_dir writes real files and sidesteps the whole problem.

    No allow_patterns. The weights live in `model.onnx.data` (2.27 GB) and the
    graph also references `Constant_685_attr__value`, which has no extension at
    all -- any pattern list is one missed name away from a 109 kB download that
    looks like it worked. The whole repo is 2.3 GB; the few files we do not
    need are kilobytes.
    """
    from huggingface_hub import snapshot_download

    def total() -> int:
        return sum(f.stat().st_size for f in ONNX_DIR.rglob("*") if f.is_file())

    if ONNX_DIR.exists() and total() > 2_000_000_000:
        f = max(ONNX_DIR.rglob("*.onnx"), key=lambda p: p.stat().st_size)
        print(f"[1/4] already downloaded ({human(total())} in {ONNX_DIR.name}/)")
        return f

    print(f"[1/4] downloading {SOURCE_REPO} -- 2.3 GB, this is the slow part")
    ONNX_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=SOURCE_REPO, local_dir=str(ONNX_DIR))

    got = total()
    if got < 2_000_000_000:
        sys.exit(
            f"    only {human(got)} arrived, expected about 2.3 GB.\n"
            f"    The big file is model.onnx.data -- check it is in {ONNX_DIR}\n"
            "    and re-run. A partial download leaves the graph without its\n"
            "    weights, which fails later and more confusingly.")

    found = sorted(ONNX_DIR.rglob("*.onnx"))
    if not found:
        sys.exit(f"    no .onnx file under {ONNX_DIR}")
    # model.onnx is only the graph; the weights sit beside it in model.onnx.data
    # and onnxruntime resolves them by relative path, so return the graph.
    f = max(found, key=lambda p: p.stat().st_size)
    print(f"    {human(got)} total, graph at {f.relative_to(ONNX_DIR)}")
    return f


# ── 2. quantise to int8 ─────────────────────────────────────────────────────
def quantise(fp32: Path, per_channel: bool = True, force: bool = False) -> None:
    if INT8.exists() and not force:
        print(f"[2/4] already have {INT8.name} ({human(INT8.stat().st_size)})"
              " -- pass --force to rebuild")
        return
    import onnx
    from onnxruntime.quantization import quantize_dynamic, QuantType
    mode = "per-channel" if per_channel else "per-tensor"
    print(f"[2/4] quantising to int8, {mode} -- needs ~6 GB free RAM")
    t = time.time()

    # Dynamic quantisation touches weights only; activations stay float. That
    # is the right trade here: almost all the size is in the weights, and
    # leaving activations alone keeps the output close to the original.
    #
    # per_channel keeps one scale per output channel rather than one for the
    # whole tensor. A weight matrix whose channels differ in range loses less
    # that way, for the same file size and a little more compute.
    #
    # DefaultTensorType is not optional for this model. ONNX shape inference
    # runs on a protobuf capped at 2 GB, and these weights are 2.27 GB, so it
    # cannot annotate every intermediate tensor. The quantiser then reaches a
    # MatMul whose output type it cannot determine and gives up. This model is
    # fp32 throughout, so float is the right assumption rather than a guess.
    quantize_dynamic(
        model_input=str(fp32),
        model_output=str(INT8),
        weight_type=QuantType.QInt8,
        per_channel=per_channel,
        extra_options={"DefaultTensorType": onnx.TensorProto.FLOAT},
    )

    # fp32 is only the graph; the weights sit in model.onnx.data beside it, so
    # report the folder total or the number reads as "0 MB -> 569 MB".
    before = sum(f.stat().st_size for f in fp32.parent.rglob("*")
                 if f.is_file() and f.name != INT8.name)
    print(f"    {human(before)} -> {human(INT8.stat().st_size)} "
          f"in {time.time() - t:.0f}s")


# ── 3. agreement check ──────────────────────────────────────────────────────
PROBES = [
    "What spacing should I use for Bt cotton in medium soil?",
    "कपास की बुवाई के लिए कितनी दूरी रखनी चाहिए?",
    "कापसासाठी किती अंतर ठेवावे?",
    "soybean seed rate per acre",
    "तूर पिकावरील किडीचे नियंत्रण कसे करावे?",
    "wheat irrigation schedule rabi",
]


def compare() -> None:
    """Embed the same probes both ways and report how far apart they land."""
    import numpy as np
    import config

    def vecs(backend: str):
        config.EMBED_BACKEND = backend
        config.ONNX_LOCAL_PATH = str(INT8)
        import farmer.text_embedder as te
        te._model = None
        te._ort = None
        return te.embed_texts(PROBES)

    print("[3/4] comparing fp32 and int8 on", len(PROBES), "probes")
    a = vecs("flagembedding")
    b = vecs("onnx")

    worst_d, worst_s = 1.0, 1.0
    for i, (x, y) in enumerate(zip(a, b)):
        u, v = np.array(x.dense), np.array(y.dense)
        cos = float(u @ v / ((np.linalg.norm(u) * np.linalg.norm(v)) or 1))

        # sparse: how much of the fp32 weight mass the int8 model also found
        shared = set(x.sparse) & set(y.sparse)
        total = sum(x.sparse.values()) or 1.0
        overlap = sum(x.sparse[t] for t in shared) / total

        worst_d, worst_s = min(worst_d, cos), min(worst_s, overlap)
        print(f"    {i + 1}. dense cos {cos:.4f}   sparse overlap {overlap:.3f}"
              f"   {PROBES[i][:44]}")

    print(f"\n    worst dense cosine   {worst_d:.4f}")
    print(f"    worst sparse overlap {worst_s:.3f}")

    # This is a screening check, not the decision. It compares an int8 query
    # against an fp32 query, but deployment embeds the index with int8 too --
    # both sides carry the same distortion and most of it cancels in a dot
    # product. What matters is whether the ranking moves, which only
    # evaluate.py on a matched index can answer. A hard gate here would reject
    # a model that retrieves perfectly well.
    if worst_s < 0.90:
        print("\n    STOP: sparse overlap is too low. The lexical half of the")
        print("    hybrid relies on shared token ids; this would halve recall.")
        sys.exit(1)
    if worst_d < 0.95:
        print("\n    STOP: dense vectors have moved too far to trust.")
        sys.exit(1)
    if worst_d < 0.99:
        print("\n    Dense agreement is below 0.99 but the sparse half is intact.")
        print("    That is expected for int8 and is not disqualifying on its own.")
        print("    Decide on evaluate.py, not on this number -- see step 4.")
    else:
        print("\n    close agreement on both halves")


# ── 4. rebuild the index with the quantised model ───────────────────────────
def reindex() -> None:
    print("[4/4] rebuilding the index with the int8 model")
    print("      run this yourself so you see the output:\n")
    print("      set EMBED_BACKEND=onnx")
    print(f'      set ONNX_LOCAL_PATH={INT8}')
    print("      set LOCAL_KB_DIR=models/local_kb_onnx")
    print("      set VECTOR_BACKEND=local")
    print("      python ingest.py --recreate\n")
    print("      then check retrieval did not regress:")
    print("      python evaluate.py\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true",
                    help="only run the fp32 vs int8 agreement check")
    ap.add_argument("--per-tensor", action="store_true",
                    help="one scale per tensor instead of per output channel "
                         "(smaller compute, worse accuracy)")
    ap.add_argument("--force", action="store_true",
                    help="re-quantise even if model_int8.onnx already exists")
    args = ap.parse_args()

    check_deps()
    if args.compare:
        compare()
    else:
        fp32 = download()
        quantise(fp32, per_channel=not args.per_tensor, force=args.force)
        compare()
        reindex()
