"""
Looking at a photograph of a sick plant.

The honest version of crop disease detection.

What this does and does not do
------------------------------
The vision model is asked for one thing only: describe what is visible. Which
crop, which part, what the marks look like, where they sit on the leaf. It is
explicitly told not to prescribe anything.

Treatment does not come from here. The description it produces becomes a
retrieval query against the agricultural documents, and the advice a farmer
reads is written from those -- the same path every other answer in this app
takes. A vision model recalling a pesticide dose from its training data is
exactly the kind of confident, unsourced, occasionally wrong answer this
project exists to avoid.

So the chain is:

    photo -> "what do you see?" -> symptoms -> search the documents -> advice
                                                 ^^^^^^^^^^^^^^^^^^
                                                 the part that is grounded

Why there is a confidence floor
-------------------------------
A leaf spot photographed at arm's length in poor light is genuinely ambiguous;
bacterial blight, early blight and a nutrient deficiency can all look like
brown patches. Below VISION_MIN_CONFIDENCE this module refuses to name a
disease and asks for a better photograph instead. A farmer who sprays on a
40%-confident guess has spent money, lost time, and still has the problem.

This is a second opinion, not a diagnosis. Nothing in here should ever be the
only thing standing between a farmer and a spray tank.
"""

from __future__ import annotations

import base64
import io
import json
import re
from dataclasses import dataclass, field

import config

# The model is asked for strict JSON. These are the keys we rely on; anything
# else it volunteers is ignored rather than trusted.
_LOOK_PROMPT = """You are helping an agricultural advisor in Maharashtra, India.

Look at this photograph of a plant and describe ONLY what you can actually see.

Rules:
- Do NOT recommend any pesticide, fungicide, fertiliser, dose or product.
- Do NOT state a diagnosis as fact. Give candidates with honest confidence.
- If the photo is too blurry, too dark, too far away, or shows no plant,
  say so and give an empty candidate list.
- Confidence is 0-100 and must reflect real uncertainty. Brown patches on a
  leaf are consistent with several different causes; say so.

Reply with ONLY a JSON object, no other text:

{
  "crop": "the crop if identifiable, else empty string",
  "plant_part": "leaf | stem | fruit | root | whole plant | unclear",
  "visible": ["short factual observations, e.g. 'yellow halo around brown spots'"],
  "candidates": [
    {"name": "possible cause", "confidence": 0-100,
     "tells": "what in a closer photo would confirm or rule this out"}
  ],
  "photo_problem": "empty string, or what makes this photo hard to read"
}"""


@dataclass
class Candidate:
    name: str
    confidence: int
    tells: str = ""


@dataclass
class Observation:
    """What the model says it can see. Never a diagnosis."""

    crop: str = ""
    plant_part: str = ""
    visible: list[str] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    photo_problem: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    @property
    def confident_enough(self) -> bool:
        """Is the best candidate strong enough to be worth naming at all?"""
        if not self.candidates:
            return False
        return self.candidates[0].confidence >= config.VISION_MIN_CONFIDENCE

    @property
    def best(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None

    def search_query(self) -> str:
        """
        What to look up in the documents.

        Built from the crop and the visible symptoms rather than the candidate
        name, deliberately. Searching for "early blight" finds documents that
        already agree with the model; searching for what is actually on the
        leaf can turn up the cause it did not consider.
        """
        parts = [self.crop] if self.crop else []
        parts += self.visible[:4]
        if self.best is not None:
            parts.append(self.best.name)
        return " ".join(p for p in parts if p).strip()


def shrink(image_bytes: bytes, max_side: int | None = None) -> bytes:
    """
    Make a phone photo small enough to send.

    Groq charges a flat 2048 tokens per image regardless of size, so a 6 MB
    original buys nothing over a 1024px one -- it only costs upload time on a
    rural connection. Returns the original unchanged if Pillow is missing or
    the image cannot be read, because a slow send beats no send.
    """
    max_side = max_side or config.VISION_MAX_PIXELS
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("RGB")
        if max(image.size) > max_side:
            scale = max_side / max(image.size)
            image = image.resize(
                (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                Image.LANCZOS)
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=82, optimize=True)
        return out.getvalue()
    except Exception:
        return image_bytes


def _parse(raw: str) -> Observation:
    """
    Read the model's JSON, defensively.

    Models wrap JSON in prose and in ```json fences no matter how firmly you
    ask them not to, so we find the object rather than trusting the envelope.
    """
    text = (raw or "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return Observation(error="The model did not return a readable result.")

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return Observation(error="The model's result could not be read.")

    if not isinstance(data, dict):
        return Observation(error="The model's result was not in the expected shape.")

    candidates = []
    for item in (data.get("candidates") or []):
        if not isinstance(item, dict) or not item.get("name"):
            continue
        try:
            confidence = int(float(item.get("confidence", 0)))
        except (TypeError, ValueError):
            confidence = 0
        candidates.append(Candidate(
            name=str(item["name"])[:120],
            confidence=max(0, min(100, confidence)),
            tells=str(item.get("tells", ""))[:300],
        ))
    candidates.sort(key=lambda c: c.confidence, reverse=True)

    visible = [str(v)[:200] for v in (data.get("visible") or [])
               if isinstance(v, (str, int, float))]

    return Observation(
        crop=str(data.get("crop", ""))[:80],
        plant_part=str(data.get("plant_part", ""))[:40],
        visible=visible[:8],
        candidates=candidates[:4],
        photo_problem=str(data.get("photo_problem", ""))[:300],
    )


def look(image_bytes: bytes) -> Observation:
    """
    Ask the vision model what it can see. Never raises.

    Returns an Observation whose `error` is set if anything went wrong, so the
    screen has one thing to check rather than a try/except around the call.
    """
    if not image_bytes:
        return Observation(error="No photograph was given.")
    if len(image_bytes) > config.VISION_MAX_BYTES:
        return Observation(error="That photograph is too large to send.")
    if not config.GROQ_API_KEY:
        return Observation(error="No model key is set, so the photo cannot be read.")

    payload = shrink(image_bytes)
    encoded = base64.b64encode(payload).decode("ascii")

    # imported here so the module can be tested, and the screen imported,
    # without the groq package present
    from farmer import answer_writer

    try:
        client = answer_writer._groq_client()
        response = client.chat.completions.create(
            model=config.GROQ_VISION_MODEL,
            temperature=0.1,          # describing, not inventing
            max_tokens=900,
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": _LOOK_PROMPT},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
                ],
            }],
        )
    except Exception as exc:
        _, message = answer_writer.classify_failure(exc)
        return Observation(error=message)

    try:
        raw = response.choices[0].message.content or ""
    except (AttributeError, IndexError):
        return Observation(error="The model returned nothing to read.")

    return _parse(raw)
