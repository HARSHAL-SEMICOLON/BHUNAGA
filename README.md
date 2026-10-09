# Bhunaga (भुनागा) — Trilingual (Marathi / Hindi / English) Agricultural RAG

A retrieval-augmented question-answering pipeline for Indian farmers that takes
a question in **Marathi, Hindi, or English** and answers in the **same
language**, retrieving from a mixed-language knowledge base (e.g. ICAR docs)
without any lossy "translate-to-English-first" step.

Built entirely on a free / local stack.

## How it works

```
question ──► [language detection]──► [hybrid retrieval] ──► [generation] ──► answer
             lingua detector          BGE-M3 dense+sparse     GPT-OSS 120B     (same language)
             (hi vs mr by model,       over Qdrant             via Groq
              not script)                                      + optional IndicTrans2
```

Two design decisions carry the trilingual support:

1. **One multilingual embedding model — BGE-M3.** It covers Marathi, Hindi and
   English in a single vector space, so a Marathi query embeds straight against
   English documents. It emits **both dense and sparse** vectors, so the hybrid
   layer needs no separate BM25 index.
2. **Detect once, carry as a tag, reply in it.** Language is detected up front
   with `lingua` and threaded into the generation prompt
   (`Answer in {language}`). Hindi and Marathi share Devanagari script, so a
   real language-ID model is required — script alone can't separate them.

## Project layout

```
app.py                the Streamlit app — wiring only, ~60 lines
config.py             all settings (models, backend, Marathi strategy)
ingest.py             load → chunk → tag language → embed → store
query.py              detect → retrieve → generate (CLI + interactive)

farmer/                       everything that is not a screen
  language_detector.py  finds the language (English / Hindi / Marathi)
  text_embedder.py      turns text into BGE-M3 vectors (dense + sparse)
  vector_database.py    picks a backend, then talks to it
  local_store.py        the on-disk fallback index for when Qdrant is down
  searcher.py           hybrid search + same-language bonus
  answer_writer.py      writes the answer, alone or via the council
  assistant.py          the whole pipeline with no screen attached
  intent.py             is this a document question, or live data?
  question_bank.py      the trilingual question list behind cards + autocomplete
  text.py               every interface string, in all three languages
  voice.py              speech → text with Whisper on Groq
  geo.py                village → coordinates, cached on disk
  spray.py              which hours are safe to spray, and why
  soil.py               soil at the farm's own coordinates
  scoring.py            simple scores used by the tests
  farmer_profile.py     saves the farmer's details
  daily_advice.py       the "what to do today" tips
  cost_calculator.py    cost and profit maths
  mandi_prices.py       market prices (with safe fallbacks)
  weather.py            weather + crop alerts
  council/                    the three-expert council (see below)
    roles.py              who the three experts are and what each is told
    member.py             one expert reading the documents
    agreement.py          how much they agreed, measured without a model
    chairman.py           merges the opinions, scores the agreement

ui/                           everything the farmer sees
  theme.py              the stylesheet and the bar across the top
  nav.py                which screen we are on, and the buttons that change it
  sidebar.py            profile, knowledge base, settings
  home.py               the picture-first landing screen
  ask.py                the question screen — speak, tap, or type
  council_view.py       the council's deliberation panel
  speak.py              read the answer aloud, in the browser
  tools.py              Today, Money and Market

channels/                     ways in that are not the web app
  webhook.py            WhatsApp messages and IVR calls, over Twilio

check_apis.py         one command that says which service is broken and why
docker-compose.yml    local Qdrant
data/                 the knowledge base — crops, schemes, soil, pests, selling
```

## Setup

**Works on Python 3.10 through 3.14.** All dependencies ship prebuilt wheels
(verified for 3.14 on Windows). No C compiler or Visual Studio Build Tools needed.

```bash
# 1. Create an isolated environment (use whatever Python you have, 3.10+)
#    Windows:  py -m venv .venv  &&  .\.venv\Scripts\Activate.ps1
#    macOS/Linux:  python3 -m venv .venv  &&  source .venv/bin/activate

# 2. Install deps (first run pulls BGE-M3 + torch, ~2 GB)
pip install -r requirements.txt

# 3. Configure secrets  (already done if you have a .env)
cp .env.example .env      # add your Groq key + Qdrant URL/key

# 4. Qdrant: nothing to run if you use Qdrant Cloud (just set QDRANT_URL/KEY).
#    For a local instance instead:  docker compose up -d
```

Language detection uses `lingua` (pure-Python, no compiler, no model download).
The BGE-M3 embedding model downloads automatically on the first `ingest`/`query`.

## Usage

```bash
# Add documents (PDF / DOCX / TXT / MD), mixed languages are fine
cp your_icar_docs/*.pdf data/
python ingest.py                      # or: python ingest.py --recreate

# Ask — in any of the three languages
python query.py "How much urea per acre for wheat?"
python query.py "गव्हासाठी प्रति एकर किती युरिया लागते?"
python query.py "गेहूं के लिए कितनी यूरिया चाहिए?" --show-context
python query.py --interactive
```

## The council of experts (multi-agent consensus)

One model answering alone has no one to check it. A wrong fertiliser dose reads
exactly like a right one. So the answer can instead be produced by a small
council: three experts read the *same* retrieved chunks from three different
angles, and a chairman merges what they say.

```
question + retrieved chunks
         │
  ┌──────┼──────┐
  ▼      ▼      ▼
🌱 Agronomist   💰 Farm Economist   📜 Scheme Officer
 dose, timing    cost, yield, risk   eligibility, subsidy
  └──────┼──────┘        (any of them may stay quiet)
         ▼
   🧑‍⚖️ Chairman  ──►  merged answer + agreement score + list of clashes
```

Three points worth defending in a viva:

1. **Different jobs, not different seeds.** Running one prompt three times gives
   you the same answer three times. Each seat has its own remit, so the opinions
   genuinely differ and agreement between them means something.
2. **Silence is a valid answer.** "How much urea per acre" has nothing in it for
   the Scheme Officer, so it replies `NO_INPUT` and is dropped from the count.
   A council where everyone always talks is not a council.
3. **The agreement score is not self-reported.** The chairman gives a number,
   but we separately measure word overlap between the opinions in
   `council/agreement.py` — no model involved — and blend the two 70/30. The UI
   shows both, so you can see when the chairman is flattering itself.

Every failure degrades instead of crashing: an expert that errors is marked
failed, one lone speaker skips the chairman entirely, and if the whole council
falls over the app quietly serves the plain single-model answer.

```bash
python query.py "How much urea per acre for wheat?" --show-panel   # see all three
python query.py "..." --no-council                                 # single model
COUNCIL_ENABLED=0 streamlit run app.py                             # off by default
```

In the app there is a sidebar toggle, a consensus bar under every answer, and a
**How the council decided** panel with one card per expert.

## Reaching farmers who cannot read

An advisory app that assumes literacy excludes a large share of the people it is
supposed to serve. So there are three ways to ask the same question, and none of
them is the "accessible version" of the others — they are all the front door.

| | For whom | How it works |
|---|---|---|
| 🎤 **Speak it** | cannot read or write | Records in the browser, transcribed by Whisper on Groq. Handles Marathi and Hindi. Nothing is stored. |
| 👆 **Tap a card** | reads a little, will not type Devanagari | 20 common questions with their own icons, grouped under five topics that also have icons. |
| ⌨️ **Type it** | comfortable with a keyboard | Suggestions appear while typing, matched across all three languages at once. |
| 🔊 **Hear it back** | cannot read the answer either | Every answer has a Listen button. Uses the browser's own speech engine — no key, no cost, works offline once the page is open, and the audio never leaves the phone. |

That last row matters more than it looks. Voice input without voice output is
half a bridge: the farmer speaks the question and then arrives at a screen full
of text they cannot read.

Supporting decisions:

- **The whole interface is trilingual, not just the answers.** Every string lives
  in `farmer/text.py`; no screen is allowed to hard-code English, and a test
  fails the build if any string is missing a translation or if a screen still
  carries its own translation table.
- **The language switch is the first thing in the sidebar, outside the profile
  form.** Inside the form it would not apply until the farmer found and pressed
  Save — a lot to ask of someone who cannot read the form they are looking at.
- **Navigation is pictures first.** Five big tiles, icon above the word, and the
  word is in the farmer's own language. The previous version opened with a
  paragraph of English and a row of small text tabs.
- **Romanised input is expected, not tolerated.** A phone keyboard opens on
  English letters, so `kanda`, `bhav` and `kenchua` all find the right questions.
- **Nothing is explained by colour alone.** Every state carries an icon or a word
  as well — red/green colour blindness is common among older men, which is most
  of the intended users.
- **Every tap target is at least 48 px.** This gets used on a phone, outdoors.

## Three ways in: app, WhatsApp, phone call

Not every farmer has a smartphone, and plenty who do are on a connection that
will not load a web app. So the assistant is deliberately not part of the
Streamlit code. `farmer/assistant.py` takes a question and returns an answer,
knowing nothing about screens; each channel just converts its own message format
into a question and back again.

```
Streamlit  ─┐
WhatsApp   ─┼─►  assistant.ask()  ─►  intent ─► retrieval ─► council ─► answer
IVR call   ─┘
```

```bash
pip install fastapi uvicorn
python channels/webhook.py        # POST /whatsapp, POST /voice, GET /health
ngrok http 8000                   # Twilio needs a public HTTPS URL
```

A WhatsApp reply names its sources and, when the council's agreement score is
low, says so in words — on a phone there is no panel to expand, so a
disagreement has to be stated or it is invisible. The IVR path records the
caller, transcribes with Whisper, and reads the answer back with the citation
markers and bullets stripped out, because those are meaningless out loud.

**Honestly stated:** the webhook is written against Twilio's documented request
and TwiML formats and is fully tested offline, but it has not been run against
Twilio's live servers — the account, number and public URL are yours to supply.
Everything below the webhook is the same code the web app uses.

## Knowing what kind of question it is

`farmer/intent.py` classifies every question before retrieval: price, weather,
spray, scheme, or general advice.

This exists because some questions **cannot** be answered from documents. "What
is onion selling for today?" has no answer in a PDF — retrieving a storage guide
and generating a confident paragraph from it would be worse than useless. Those
questions get routed to the live screen instead, with a line saying why.

It is a keyword matcher, not a model call, and deliberately so: it runs in under
a millisecond, costs nothing on a free tier already carrying four calls per
question, and when it is wrong you can see exactly which word did it. Every
keyword is listed in all three languages, because a Marathi speaker asking about
price says भाव, not "price".

## The outside services

Everything here is free. Only one needs a key at all.

| What | Service | Key? | Used for |
|---|---|---|---|
| Answers, voice | Groq (GPT-OSS 120B, Whisper) | yes, free | the council, and speech → text |
| Village → coordinates | Open-Meteo geocoding | no | cached on disk, looked up once per village |
| Weather, 7-day outlook | Open-Meteo forecast | no | sowing and harvest timing |
| Spray window | Open-Meteo hourly | no | which hours today are safe to spray |
| Soil at the farm | ISRIC SoilGrids | no | pH, organic carbon, texture |
| Mandi prices | data.gov.in (Agmarknet) | optional | live market rates |

**The spray window is the one worth demonstrating.** Spraying in the wrong wind
blows the chemical off the field; rain within a few hours washes it off. Both
mean the money was spent for nothing. Open-Meteo gives hourly wind, rain
probability and temperature for free, so every daylight hour of the next two days
is scored and the good stretches are named — "Sunday 09:00–12:00". Every rejected
hour says why it was rejected, so it is not a black box.

### When prices come back as samples

`filters[state]` and `min_price` are an older data.gov.in spelling; the current
API also answers to `filters[State.keyword]` and `Min_Price`. Guessing wrong does
not raise an error — it returns HTTP 200 with zero records, which is exactly how
this app ended up quietly showing sample prices while appearing to work.

So the client does not guess. It tries each spelling until one returns rows,
remembers the winner, and reads every column through a list of aliases. If every
filtered call fails it fetches unfiltered and filters in Python, which works as
long as the feed is up at all.

```bash
python check_apis.py --raw     # prints what every service actually returned
```

That script is the fastest way to find out what is wrong. For prices it prints
the real field names and the filter style that worked.

## When Qdrant is not there

A free Qdrant Cloud cluster is switched off after a few idle weeks. Finding that
out on the morning of a demo is a bad time to find it out, so `VECTOR_BACKEND`
defaults to `auto`: try Qdrant, and if it does not answer, fall back to
`farmer/local_store.py` — the same dense + sparse hybrid search with the same RRF
fusion, in numpy, over two files on disk.

It is honest about the trade-off. There is no index; every search compares
against every chunk. On a few thousand chunks that is a couple of milliseconds.
On a million you want the real Qdrant back.

```bash
VECTOR_BACKEND=auto    streamlit run app.py   # try cloud, fall back  (default)
VECTOR_BACKEND=local   streamlit run app.py   # never touch the network
VECTOR_BACKEND=qdrant  streamlit run app.py   # cloud only, fail loudly
```

The sidebar always says which backend is live, and if it fell back it says why
in one line ("the cluster answered 404 — it was probably deleted, or it is older
than Qdrant 1.9") rather than showing a stack trace.

## The Marathi A/B switch (publication-worthy)

Groq's GPT-OSS 120B handles English and Hindi well and Marathi reasonably.
Where Marathi output quality dips, you can keep reasoning in English and only
translate the final answer with IndicTrans2. This is a config flag so you can
compare both paths in evaluation:

```bash
MARATHI_STRATEGY=native          python query.py "..."   # answer directly in Marathi
MARATHI_STRATEGY=translate_after python query.py "..."   # reason in English, translate output
```

Each answer prints which strategy produced it, so you can report
"native Marathi generation vs translate-after" as a result.

For the `translate_after` path, also install IndicTrans2:

```bash
pip install transformers torch sentencepiece
pip install git+https://github.com/VarunGumma/IndicTransToolkit.git
```

## Knowledge base notes

The corpus **is** mixed-language, not merely allowed to be: 24 documents, of
which two are written in Marathi (`mr_kanda_lagvad.md`, `mr_gandulkhat.md`) and
two in Hindi (`hi_gehu_kheti.md`, `hi_sarkari_yojana.md`), each a full source
document rather than a token translation.

This is load-bearing. An all-English corpus would leave `SAME_LANG_BOOST` with
nothing to boost and make the `same_lang` metric zero by construction for every
Hindi and Marathi query — the feature would exist in the code and never fire
once. A test in `tests/test_gaps.py` fails if the corpus ever drifts back to
being single-language.

Each chunk is tagged with its detected source language (`source_lang`). BGE-M3
retrieves across languages regardless — a Marathi question matches an English
document — and `SAME_LANG_BOOST` in `config.py` can weight same-language
evidence up at fusion time.

**It is off by default, because measuring it killed it.** The boost began life
as a flat `+0.10` added to the fused score. Qdrant returns RRF scores of about
0.01–0.03, so that addition was several times the entire spread: every chunk in
the query's language sorted above every chunk that was not, whatever either one
said. A feature described as a nudge was a hard language filter, and it was
switching off the cross-lingual retrieval this project exists to demonstrate.

Re-applied as a ratio it behaves as intended, and it still does not pay:

| keyword recall | en | hi | mr | mr MRR | mr same_lang |
|---|---|---|---|---|---|
| additive `+0.10` (the bug) | 0.46 | 0.33 | 0.33 | 0.74 | 1.00 |
| ratio `×1.10` | 0.46 | 0.55 | 0.48 | 0.76 | 0.71 |
| no boost | 0.46 | **0.60** | **0.54** | **0.81** | 0.64 |

English is flat across all three, which is the control: 83% of the corpus is
English, so the boost is close to a no-op there, and a harness that moved
English would be measuring something other than what it claims.

Two things worth taking from this. BGE-M3's shared vector space needed no help —
the hand-built heuristic on top of it only subtracted. And `same_lang` is a
diagnostic, not a target: it moves *against* quality, falling 1.00 → 0.71 → 0.64
for Marathi while recall climbs. A high `same_lang` means the retriever was
confined, not that it was confident.

Reproduce with `SAME_LANG_BOOST=0.10 python evaluate.py --no-generate`. Caveat
worth stating out loud: n=12 questions. The additive-versus-anything gap is far
too large to be noise; ratio versus off is suggestive, not settled.

## Evaluation

A harness runs the question set across all three languages and scores both
retrieval and generation. The question set (`eval/questions.json`) holds the
**same question in en/hi/mr**, so you also measure cross-language consistency.

```bash
# retrieval-only — no Groq key needed, fast sanity check
python evaluate.py --no-generate

# THE headline number: one model alone vs the council
python evaluate.py --council both

# A/B the two Marathi strategies
python evaluate.py --mr-strategies native translate_after

# just Marathi, both comparisons at once
python evaluate.py --langs mr --council both --mr-strategies native translate_after
```

Metrics (`farmer/scoring.py`, no extra libraries):

| Metric | Meaning |
|---|---|
| `hit@k` | a relevant keyword appears anywhere in the top-k chunks |
| `keyword_recall` | fraction of expected keywords found in top-k |
| `MRR` | 1 / rank of the first relevant chunk |
| `same_lang` | fraction of retrieved chunks in the query's language — a diagnostic, not a score to maximise (see the boost ablation above) |
| `lang_ok` | answer came back in the requested language (re-detected) |
| `answer_kw` | did the model actually *use* what retrieval found |
| `grounded` | **fraction of the numbers in the answer that appear in the sources** |

`grounded` is the one that makes the multi-agent claim testable. Advice to a
farmer is mostly numbers — 50 kg of urea, ₹6,000, 72 hours — and a number the
model invented is exactly the mistake that costs a season. Waffly prose is
harmless; a wrong dose is not. Devanagari digits are normalised, so ५० and 50
count as the same number.

`--council both` runs every question twice and prints a direct comparison:

```
metric                   single   council    change
answer keyword recall      0.xx      0.xx     +0.xx
numbers traceable          0.xx      0.xx     +0.xx
answered in language       0.xx      0.xx     +0.xx
```

Without that table, "we added multi-agent consensus" is a claim. With it, it is
a result — and if the council does *not* help, that is a finding worth reporting
honestly too.

All 12 questions in `eval/questions.json` are answerable from a real file in
`data/`, and every one names its `expected_source`, so `source_match` measures
something. Four target the Marathi and Hindi documents specifically, which is
where `SAME_LANG_BOOST` has work to do. Keyword grading is accent- and
case-insensitive and cross-script, because the keyword lists carry en/hi/mr
variants of each fact.

## Free-stack summary

| Layer            | Component                         | Cost  |
|------------------|-----------------------------------|-------|
| Language ID      | lingua (pure-Python)              | free  |
| Embeddings       | BGE-M3 (dense + sparse)           | free  |
| Vector store     | Qdrant (local Docker)             | free  |
| Generation       | GPT-OSS 120B via Groq             | free* |
| Marathi fallback | IndicTrans2 (local)               | free  |

\* Groq free tier, rate-limited.
