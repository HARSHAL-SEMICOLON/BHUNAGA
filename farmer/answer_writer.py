"""
Write the final answer with the Groq AI model (GPT-OSS 120B).

We always tell the model which language to answer in, so it never guesses. It
answers only from the documents we give it.

For Marathi there are two ways:
  - "native"          -> the model answers in Marathi directly
  - "translate_after" -> the model answers in English, then we translate it to
                         Marathi. This can keep the thinking clearer.

There are also two ways to reach the answer itself. The plain one is a single
model call. The other is the council (farmer/council/), where three experts each
give an opinion and a chairman merges them. COUNCIL_ENABLED in config picks
which one, and if the council fails for any reason we quietly use the plain one
so the farmer still gets an answer.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any

import config
from farmer.searcher import RetrievedChunk

_groq = None
_indictrans = None  # the translate tool. we load it only when we need it

# How many times a transient failure is retried, and how long we wait between
# attempts. Deliberately small: a farmer watching a spinner would rather be
# told it failed than wait a minute to be told the same thing.
MAX_RETRIES = 2
BACKOFF_SECONDS = (1.0, 3.0)

# Running total of what we have spent with the provider this process.
#
# The free Groq tier is capped on *tokens per day*, not requests, and a full
# three-arm evaluation is several times that cap. Guessing from character
# counts is not good enough to budget against a hard limit, so we read the real
# usage the API reports and let evaluate.py stop before it gets cut off
# mid-question.
_USAGE = {"calls": 0, "prompt": 0, "completion": 0, "total": 0}


def tokens_used() -> dict:
    """What this process has spent so far. A copy, so callers cannot edit it."""
    return dict(_USAGE)


def reset_tokens() -> None:
    for key in _USAGE:
        _USAGE[key] = 0


def _record_usage(resp) -> None:
    """Add one response to the running total. Never raises."""
    _USAGE["calls"] += 1
    usage = getattr(resp, "usage", None)
    if usage is None:
        return
    for field, key in (("prompt_tokens", "prompt"),
                       ("completion_tokens", "completion"),
                       ("total_tokens", "total")):
        value = getattr(usage, field, None)
        if isinstance(value, int):
            _USAGE[key] += value


@dataclass
class Answer:
    text: str
    lang: str
    strategy: str
    used_chunks: list[RetrievedChunk]
    council: Any = None       # a council.Council when the council ran, else None
    cached: bool = False      # served from _ANSWERS without calling the model


# Finished answers, newest last. In memory only: it survives Streamlit reruns
# (the module stays loaded) and dies with the process, which is the right
# lifetime -- a cached answer is a convenience, not a record.
_ANSWERS: dict[str, Answer] = {}


def _cache_key(query: str, lang: str, chunks: list[RetrievedChunk],
               variant) -> str:
    """
    What makes two questions the same question.

    The retrieved chunks are part of the key, not just the query. Re-ingesting
    the corpus changes what the answer should be, and a cache that ignored that
    would keep serving advice from documents that have since been replaced.

    `variant` is how the answer was produced — single, council or
    self-consistency. It has to be in the key or the three arms of the
    evaluation would serve each other's answers and all score identically.
    """
    material = "\u0000".join([
        query.strip(), lang, str(variant), config.GROQ_MODEL,
        config.MARATHI_STRATEGY, *(c.text for c in chunks),
    ])
    return hashlib.sha1(material.encode("utf-8")).hexdigest()


def clear_cache() -> None:
    """Forget every cached answer. Called after the corpus changes."""
    _ANSWERS.clear()


# Groq
def _groq_client():
    global _groq
    if _groq is None:
        from groq import Groq
        if not config.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set (see .env.example).")
        _groq = Groq(api_key=config.GROQ_API_KEY)
    return _groq


def classify_failure(exc: Exception) -> tuple[str, str]:
    """
    Work out what kind of model failure this is, and what to say about it.

    Returns (kind, message) where kind is one of:

      "daily"     the free tier's tokens-per-day budget is gone. Retrying is
                  pointless -- it will not come back until the quota resets --
                  so the only useful response is to say so in those words.
      "burst"     too many requests too quickly. Worth one short wait.
      "transient" a 5xx or a dropped connection. Worth a retry.
      "auth"      the key is missing, wrong, or revoked. Never retryable.
      "other"     anything else.

    This exists as a pure function because the distinction that matters most
    -- per-day versus per-minute -- is invisible in the status code. Both are
    429. The difference is in the message text, and getting it wrong means
    either retrying for two minutes against a wall, or giving up on something
    that would have worked on the second try.
    """
    status = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None)
    text = str(exc).lower()

    if status == 429 or "rate limit" in text or "429" in text:
        if "per day" in text or "tpd" in text or "rpd" in text:
            return ("daily",
                    "The free daily token budget for this model is used up. "
                    "It resets every 24 hours. Until then, try turning the "
                    "council off in the sidebar -- a single-model answer "
                    "costs about a quarter as much.")
        return ("burst", "Too many requests in a short time. Waiting a moment.")

    if status in (401, 403) or "api key" in text or "unauthorized" in text:
        return ("auth",
                "The model rejected the API key. Check GROQ_API_KEY in .env.")

    if status is not None and 500 <= int(status) < 600:
        return ("transient", "The model service is having trouble.")
    if any(w in text for w in ("timeout", "timed out", "connection",
                               "temporarily unavailable")):
        return ("transient", "Could not reach the model service.")
    return ("other", str(exc)[:200])


def chat(system: str, user: str, temperature: float | None = None,
         max_tokens: int | None = None, model: str | None = None) -> str:
    """
    One call to Groq. Everything that talks to the model goes through here,
    including the council, so there is only one place that knows the API shape,
    the retry policy, and what a rate limit means.
    """
    client = _groq_client()
    kwargs = dict(
        model=model or config.GROQ_MODEL,
        temperature=config.GEN_TEMPERATURE if temperature is None else temperature,
        max_tokens=max_tokens or config.GEN_MAX_TOKENS,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    if config.GROQ_REASONING_EFFORT:
        kwargs["reasoning_effort"] = config.GROQ_REASONING_EFFORT

    resp = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(**kwargs)
            break
        except Exception as exc:
            # Not every model accepts reasoning_effort, and the ones that do
            # not reject the whole request rather than ignoring the field.
            # Drop it and try again before treating this as a real failure.
            if "reasoning_effort" in kwargs:
                kwargs.pop("reasoning_effort")
                continue

            kind, message = classify_failure(exc)
            if kind in ("daily", "auth"):
                # No amount of waiting fixes either of these.
                raise RuntimeError(message) from exc
            if attempt >= MAX_RETRIES:
                raise RuntimeError(f"{message} (after {attempt + 1} attempts)") from exc
            time.sleep(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)])

    _record_usage(resp)

    text = (resp.choices[0].message.content or "").strip()
    if not text:
        # A reasoning model that spends its whole budget thinking returns an
        # empty string, not an error. Silently passing that on produces a blank
        # answer that looks like the model had nothing to say. Say what it was.
        raise RuntimeError(
            f"{kwargs['model']} returned no content. The token budget "
            f"(max_tokens={kwargs['max_tokens']}) was most likely consumed by "
            f"reasoning -- raise GEN_MAX_TOKENS or lower GROQ_REASONING_EFFORT."
        )
    return text


def _format_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[{i}] (source: {c.source}, lang: {c.source_lang})\n{c.text}")
    return "\n\n".join(blocks)


def _system_prompt(answer_lang_name: str) -> str:
    return (
        "You are an agricultural advisor for Indian farmers. "
        "Answer ONLY from the provided context. If the context does not contain "
        "the answer, say so plainly. Be concise and practical. "
        f"Answer in {answer_lang_name}, regardless of the language of the context."
    )


def _generate_with_groq(query: str, chunks: list[RetrievedChunk],
                        answer_lang_name: str) -> str:
    context = _format_context(chunks)
    return chat(
        system=_system_prompt(answer_lang_name),
        user=f"Context:\n{context}\n\nQuestion: {query}",
    )


# IndicTrans2 (translate-after path, English -> Marathi)
def _translate_en_to_mr(text: str) -> str:
    global _indictrans
    if _indictrans is None:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        from IndicTransToolkit.processor import IndicProcessor  # pip per README
        tok = AutoTokenizer.from_pretrained(config.INDICTRANS2_MODEL,
                                            trust_remote_code=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(config.INDICTRANS2_MODEL,
                                                      trust_remote_code=True)
        _indictrans = (tok, model, IndicProcessor(inference=True))

    tok, model, ip = _indictrans
    batch = ip.preprocess_batch([text], src_lang="eng_Latn", tgt_lang="mar_Deva")
    enc = tok(batch, return_tensors="pt", padding=True, truncation=True)
    out = model.generate(**enc, max_length=512, num_beams=5)
    decoded = tok.batch_decode(out, skip_special_tokens=True)
    return ip.postprocess_batch(decoded, lang="mar_Deva")[0]


# Public entry point
def generate(query: str, query_lang: str, chunks: list[RetrievedChunk],
             use_council: bool | None = None, mode: str | None = None) -> Answer:
    """
    Write the answer.

    The Marathi choice and the council choice are separate things, so we settle
    the working language first. For "translate_after" everything -- including
    the whole council debate -- happens in English and only the finished answer
    is translated. Translating each expert would cost three more model loads for
    text the farmer never reads.

    `mode` picks how the answer is produced and is what the evaluation uses:

        "single"   one model call
        "council"  three experts and a chairman
        "selfcons" the same prompt sampled four times, most typical one kept

    "selfcons" exists only as the council's control arm -- it costs the same
    four calls without the roles, so the comparison says whether the structure
    earns its keep. `use_council` is the older two-way switch and still works.
    """
    lang_name = config.LANG_NAMES.get(query_lang, "English")
    use_translate_after = (
        query_lang == "mr" and config.MARATHI_STRATEGY == "translate_after"
    )
    working_lang = "English" if use_translate_after else lang_name

    if mode is None:
        if use_council is None:
            use_council = config.COUNCIL_ENABLED
        mode = "council" if use_council else "single"
    use_council = (mode == "council")

    key = ""
    if config.GEN_CACHE_SIZE > 0:
        # the mode is part of the key: three arms answering the same question
        # must not serve each other's cached answer, or the whole comparison
        # collapses into one number repeated three times
        key = _cache_key(query, query_lang, chunks, f"mode={mode}")
        hit = _ANSWERS.get(key)
        if hit is not None:
            # move to the newest end so the busy questions survive eviction
            _ANSWERS[key] = _ANSWERS.pop(key)
            return Answer(text=hit.text, lang=hit.lang, strategy=hit.strategy,
                          used_chunks=hit.used_chunks, council=hit.council,
                          cached=True)

    panel = None
    if mode == "council":
        from farmer import council       # only load it if we are going to use it
        try:
            panel = council.deliberate(query, chunks, working_lang)
            text = panel.verdict.answer
        except Exception:
            # rate limit, timeout, every expert failing -- whatever it was, the
            # farmer still gets an answer. we just take the plain path.
            panel = None
            text = _generate_with_groq(query, chunks, working_lang)
    elif mode == "selfcons":
        from farmer import self_consistency
        try:
            panel = self_consistency.answer(query, chunks, working_lang)
            text = panel.answer
        except Exception:
            panel = None
            text = _generate_with_groq(query, chunks, working_lang)
    else:
        text = _generate_with_groq(query, chunks, working_lang)

    if use_translate_after:
        text = _translate_en_to_mr(text)

    strategy = "translate_after" if use_translate_after else "native"
    if panel is not None:
        strategy += f"+{mode}"

    answer = Answer(text=text, lang=query_lang, strategy=strategy,
                    used_chunks=chunks, council=panel)

    if key:
        _ANSWERS[key] = answer
        while len(_ANSWERS) > config.GEN_CACHE_SIZE:
            _ANSWERS.pop(next(iter(_ANSWERS)))   # drop the oldest
    return answer


def llm_text(system: str, user: str, max_tokens: int = 700) -> str:
    """Lightweight one-shot LLM call (used by the daily briefing and tools)."""
    return chat(system=system, user=user, max_tokens=max_tokens)
