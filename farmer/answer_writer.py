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

from dataclasses import dataclass
from typing import Any

import config
from farmer.searcher import RetrievedChunk

_groq = None
_indictrans = None  # the translate tool. we load it only when we need it


@dataclass
class Answer:
    text: str
    lang: str
    strategy: str
    used_chunks: list[RetrievedChunk]
    council: Any = None       # a council.Council when the council ran, else None


# Groq
def _groq_client():
    global _groq
    if _groq is None:
        from groq import Groq
        if not config.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set (see .env.example).")
        _groq = Groq(api_key=config.GROQ_API_KEY)
    return _groq


def chat(system: str, user: str, temperature: float | None = None,
         max_tokens: int | None = None, model: str | None = None) -> str:
    """
    One call to Groq. Everything that talks to the model goes through here,
    including the council, so there is only one place that knows the API shape.
    """
    client = _groq_client()
    resp = client.chat.completions.create(
        model=model or config.GROQ_MODEL,
        temperature=config.GEN_TEMPERATURE if temperature is None else temperature,
        max_tokens=max_tokens or config.GEN_MAX_TOKENS,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content.strip()


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
             use_council: bool | None = None) -> Answer:
    """
    Write the answer.

    The Marathi choice and the council choice are separate things, so we settle
    the working language first. For "translate_after" everything -- including
    the whole council debate -- happens in English and only the finished answer
    is translated. Translating each expert would cost three more model loads for
    text the farmer never reads.
    """
    lang_name = config.LANG_NAMES.get(query_lang, "English")
    use_translate_after = (
        query_lang == "mr" and config.MARATHI_STRATEGY == "translate_after"
    )
    working_lang = "English" if use_translate_after else lang_name

    if use_council is None:
        use_council = config.COUNCIL_ENABLED

    panel = None
    if use_council:
        from farmer import council       # only load it if we are going to use it
        try:
            panel = council.deliberate(query, chunks, working_lang)
            text = panel.verdict.answer
        except Exception:
            # rate limit, timeout, every expert failing -- whatever it was, the
            # farmer still gets an answer. we just take the plain path.
            panel = None
            text = _generate_with_groq(query, chunks, working_lang)
    else:
        text = _generate_with_groq(query, chunks, working_lang)

    if use_translate_after:
        text = _translate_en_to_mr(text)

    strategy = "translate_after" if use_translate_after else "native"
    if panel is not None:
        strategy += "+council"

    return Answer(text=text, lang=query_lang, strategy=strategy,
                  used_chunks=chunks, council=panel)


def llm_text(system: str, user: str, max_tokens: int = 700) -> str:
    """Lightweight one-shot LLM call (used by the daily briefing and tools)."""
    return chat(system=system, user=user, max_tokens=max_tokens)
