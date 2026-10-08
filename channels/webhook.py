#!/usr/bin/env python3
"""
WhatsApp and IVR, over a Twilio-compatible webhook.

The synopsis says a farmer can reach Bhunaga "via an app, WhatsApp or an IVR
call". The app is app.py. This is the other two.

Both are the same assistant behind a different pipe. WhatsApp sends the question
as text; the IVR path sends a recording, which Whisper turns into text. From
there it is identical to what the web app does, because farmer/assistant.py is
where the actual work lives and neither channel has an opinion about it.

    POST /whatsapp   Twilio WhatsApp message   -> TwiML <Message>
    POST /voice      an incoming phone call     -> TwiML <Record>
    POST /voice/reply  the caller's recording   -> TwiML <Say>
    GET  /health     is it up

Run it:

    pip install fastapi uvicorn
    python channels/webhook.py                 # listens on 0.0.0.0:8000

Twilio needs a public HTTPS URL, so for testing put a tunnel in front:

    ngrok http 8000

then point the Twilio sandbox at https://<your-tunnel>/whatsapp.

Note honestly: this file is written against Twilio's documented request and
TwiML formats and is fully tested offline, but it has not been run against
Twilio's live servers. The account, the number and the public URL are yours to
supply. Everything below the webhook — retrieval, the council, the answer — is
the same code the web app already uses.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farmer import assistant, voice           # noqa: E402

# Twilio caps a single WhatsApp body at 1600 characters
WHATSAPP_LIMIT = 1500

GREETING = (
    "🪱 Namaskar! I am Bhunaga, your farming assistant.\n\n"
    "Ask me anything about your crop, in English, हिंदी or मराठी.\n\n"
    "For example:\n"
    "• How much urea per acre for wheat?\n"
    "• कांदा साठवणूक कशी करावी?\n"
    "• क्या मैं पीएम-किसान के लिए पात्र हूँ?"
)

VOICE_PROMPT = {
    "en": "Namaskar. This is Bhunaga, your farming assistant. "
          "Please ask your question after the beep, then stay on the line.",
    "hi": "नमस्कार। यह भुनागा है। बीप के बाद अपना सवाल पूछें।",
    "mr": "नमस्कार. हे भुनागा आहे. बीप नंतर तुमचा प्रश्न विचारा.",
}

# Twilio's <Say> voices, so the answer is read in the right accent
SAY_LANG = {"en": "en-IN", "hi": "hi-IN", "mr": "hi-IN"}   # no Marathi voice


def twiml(body: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>'


def message_reply(text: str) -> str:
    return twiml(f"<Message>{escape(text)}</Message>")


def say_reply(text: str, lang: str = "en") -> str:
    voice_lang = SAY_LANG.get(lang, "en-IN")
    return twiml(f'<Say language="{voice_lang}">{escape(text)}</Say>')


def handle_whatsapp(body: str) -> str:
    """One WhatsApp message in, one TwiML reply out. Pure, so it is testable."""
    question = (body or "").strip()

    if not question or question.lower() in {"hi", "hello", "start", "namaskar",
                                            "नमस्कार", "हॅलो", "हैलो"}:
        return message_reply(GREETING)

    reply = assistant.ask(question)
    return message_reply(assistant.for_text_channel(reply, WHATSAPP_LIMIT))


def handle_voice_start() -> str:
    """Answer the call, ask for the question, record it."""
    prompt = escape(VOICE_PROMPT["en"])
    return twiml(
        f'<Say language="en-IN">{prompt}</Say>'
        # maxLength keeps a stuck call from recording forever; playBeep marks
        # the moment to start talking, which callers need on a bad line
        '<Record action="/voice/reply" method="POST" maxLength="20" '
        'playBeep="true" trim="trim-silence" timeout="3"/>'
        '<Say language="en-IN">I did not hear anything. Goodbye.</Say>')


def handle_voice_reply(audio_bytes: bytes) -> str:
    """Transcribe what the caller said, answer it, and read the answer back."""
    heard = voice.transcribe(audio_bytes, filename="call.wav")
    if not heard.ok:
        return say_reply("Sorry, I could not hear that clearly. "
                         "Please call again.", "en")

    reply = assistant.ask(heard.text, lang=heard.lang)
    spoken = assistant.for_voice_channel(reply)
    return say_reply(spoken, reply.lang)


# ------------------------------------------------------------------ server
def build_app():
    """
    The FastAPI app, built lazily.

    Importing FastAPI at module level would make the handlers above impossible
    to test without it installed, and they are the part worth testing.
    """
    import requests
    from fastapi import FastAPI, Form, Request
    from fastapi.responses import PlainTextResponse

    api = FastAPI(title="Bhunaga channels")
    XML = "application/xml"

    @api.get("/health")
    def health():
        return {"status": "ok", "service": "bhunaga-channels"}

    @api.post("/whatsapp", response_class=PlainTextResponse)
    async def whatsapp(Body: str = Form(default="")):
        return PlainTextResponse(handle_whatsapp(Body), media_type=XML)

    @api.post("/voice", response_class=PlainTextResponse)
    async def voice_start():
        return PlainTextResponse(handle_voice_start(), media_type=XML)

    @api.post("/voice/reply", response_class=PlainTextResponse)
    async def voice_reply(request: Request):
        form = await request.form()
        url = form.get("RecordingUrl")
        if not url:
            return PlainTextResponse(
                say_reply("I did not get your question. Goodbye.", "en"),
                media_type=XML)

        # Twilio hands us a URL, not the audio. Fetching it needs the account
        # credentials, which stay in the environment and never in this file.
        auth = (os.getenv("TWILIO_ACCOUNT_SID", ""),
                os.getenv("TWILIO_AUTH_TOKEN", ""))
        try:
            audio = requests.get(f"{url}.wav", auth=auth, timeout=25).content
        except Exception:
            return PlainTextResponse(
                say_reply("Sorry, I could not retrieve your question.", "en"),
                media_type=XML)

        return PlainTextResponse(handle_voice_reply(audio), media_type=XML)

    return api


def main() -> None:
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    print(f"Bhunaga channels listening on http://0.0.0.0:{port}")
    print("  POST /whatsapp     WhatsApp messages")
    print("  POST /voice        incoming calls")
    print("  GET  /health")
    print("\nTwilio needs a public HTTPS URL — put ngrok in front for testing.")
    uvicorn.run(build_app(), host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
