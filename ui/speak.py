"""
Read the answer out loud.

Voice input without voice output is half a bridge. A farmer who cannot read can
ask the question by speaking it, and then arrives at a screen full of text they
cannot read. This closes that.

It uses the browser's own speech synthesis rather than a cloud service. That
choice is deliberate:

  - no API key, no cost, no rate limit
  - no round trip, so it starts speaking immediately
  - it works with no internet once the page is open
  - the audio never leaves the phone

The trade-off is that the available voices belong to the device, not to us. Most
Android phones in India ship with a Hindi voice; Marathi is less common. So we
ask for Marathi, fall back to Hindi, and finally to whatever the browser has --
Hindi and Marathi share Devanagari, so a Hindi voice reading Marathi text is
accented but understandable, which is far better than silence.
"""

from __future__ import annotations

import json

import streamlit.components.v1 as components

from farmer.text import t

# browser voice tags, best first for each of our languages
VOICE_TAGS = {
    "mr": ["mr-IN", "hi-IN", "en-IN"],
    "hi": ["hi-IN", "mr-IN", "en-IN"],
    "en": ["en-IN", "en-GB", "en-US"],
}

# a long answer read start to finish is unusable; the farmer wants the gist
MAX_CHARS = 1200


def _clean(text: str) -> str:
    """
    Strip the things that sound wrong when spoken.

    Markdown bullets become pauses, not the word "asterisk", and the citation
    markers we add for traceability would otherwise be read out as numbers in
    the middle of a sentence.
    """
    import re
    text = re.sub(r"\[\d+\]", "", text)          # citation markers
    text = re.sub(r"[*_#`]+", "", text)          # markdown emphasis
    text = re.sub(r"^\s*[-•]\s*", ". ", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:MAX_CHARS]


def button(text: str, lang: str = "en", key: str = "0") -> None:
    """
    Draw a listen button under an answer.

    This is raw HTML rather than a Streamlit button on purpose. speechSynthesis
    lives in the browser, so a Streamlit button would have to round-trip to
    Python and back before anything could be spoken. Here the click is handled
    where the speech engine already is, and playback starts instantly.
    """
    spoken = _clean(text)
    if not spoken:
        return

    payload = json.dumps(spoken)
    tags = json.dumps(VOICE_TAGS.get(lang, VOICE_TAGS["en"]))
    listen = t("speak.listen", lang)
    stop = t("speak.stop", lang)
    no_voice = json.dumps(t("speak.novoice", lang))
    unsupported = json.dumps(t("speak.unsupported", lang))
    element = f"bhunaga_speak_{key}"

    components.html(f"""
    <style>
      .speakrow {{ display:flex; gap:8px; font-family:Inter,sans-serif; }}
      .speakbtn {{
        background:#fbf7ef; border:1.5px solid #c3b488; color:#2c4a1e;
        border-radius:12px; padding:10px 18px; font-weight:700; font-size:.95rem;
        cursor:pointer; min-height:44px;
      }}
      .speakbtn:hover {{ background:#fff; border-color:#2c4a1e; }}
      .speakbtn:disabled {{ opacity:.45; cursor:default; }}
      .speaknote {{ color:#8a7a5c; font-size:.8rem; align-self:center; }}
    </style>

    <div class="speakrow">
      <button class="speakbtn" id="play_{element}">{listen}</button>
      <button class="speakbtn" id="stop_{element}">{stop}</button>
      <span class="speaknote" id="note_{element}"></span>
    </div>

    <script>
    (function () {{
      const text = {payload};
      const wanted = {tags};
      const play = document.getElementById("play_{element}");
      const stop = document.getElementById("stop_{element}");
      const note = document.getElementById("note_{element}");

      if (!("speechSynthesis" in window)) {{
        play.disabled = true;
        note.textContent = {unsupported};
        return;
      }}

      // Voices load asynchronously in most browsers: getVoices() is empty on
      // the first call and fills in later, so we look them up at click time.
      function pickVoice() {{
        const voices = window.speechSynthesis.getVoices();
        for (const tag of wanted) {{
          const exact = voices.find(v => v.lang && v.lang.replace("_", "-") === tag);
          if (exact) return exact;
        }}
        for (const tag of wanted) {{
          const base = tag.split("-")[0];
          const near = voices.find(v => v.lang && v.lang.toLowerCase().startsWith(base));
          if (near) return near;
        }}
        return null;
      }}

      play.addEventListener("click", function () {{
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        const voice = pickVoice();
        if (voice) {{
          utterance.voice = voice;
          utterance.lang = voice.lang;
          note.textContent = "";
        }} else {{
          utterance.lang = wanted[0];
          note.textContent = {no_voice};
        }}
        // a little slower than default: this is advice, not a news bulletin
        utterance.rate = 0.92;
        window.speechSynthesis.speak(utterance);
      }});

      stop.addEventListener("click", function () {{
        window.speechSynthesis.cancel();
      }});
    }})();
    </script>
    """, height=64)
