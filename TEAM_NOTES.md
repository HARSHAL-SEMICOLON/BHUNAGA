# Bhunaga — team notes

A trilingual (Marathi / Hindi / English) question-answering assistant for Indian
farmers. Ask in any of the three languages, get the answer back in the same one,
grounded in farming documents rather than the model's memory — plus weather,
spray timing, mandi prices and a cost calculator.

Roughly 8,300 lines of Python across 11 commits. Everything runs on a free or
local stack; only one service needs a key.

---

## Run it in four lines

```bat
cd /d "E:\RESUME PROJECTS\FARMER"
.venv\Scripts\activate
python check_apis.py          :: says which outside service is broken, and why
streamlit run app.py
```

`check_apis.py` is the first thing to run when anything looks wrong. It prints
the live backend, the chunk count, and the real error from every external
service instead of a stack trace.

The knowledge base is already built and committed (`models/local_kb/`), so there
is nothing to load by hand. To rebuild it after changing `data/`:

```bat
python ingest.py --recreate
```

Secrets live in `.env`, which is gitignored. Copy `.env.example` and add a free
Groq key from console.groq.com/keys. Nothing else is required.

---

## How a question flows

```
question
   │
   ├─ language detection        lingua, by model not by script --
   │                            Hindi and Marathi share Devanagari
   │
   ├─ intent router             price / weather / spray / scheme / general
   │                            live-data questions skip retrieval entirely
   │
   ├─ hybrid retrieval          BGE-M3 dense + sparse, RRF fusion
   │                            a Marathi question matches an English document
   │
   ├─ the council               3 experts + a chairman  (or 1 model, toggleable)
   │
   └─ answer, in the question's language
```

The intent router matters more than it looks. "What is onion selling for today?"
has no answer in a PDF, so retrieving a storage guide and writing a confident
paragraph from it would be worse than useless. Those questions get routed to
live data instead, with a line saying why.

---

## What is in the folder

| Path | What it holds |
|---|---|
| `app.py` | the Streamlit app — wiring only |
| `config.py` | every setting, all env-overridable |
| `ingest.py` / `query.py` | build the index / ask from the command line |
| `farmer/` | all the logic, no screens |
| `farmer/council/` | the three experts, the chairman, the agreement measure |
| `ui/` | everything the farmer sees |
| `channels/webhook.py` | WhatsApp and IVR over Twilio |
| `data/` | the knowledge base, 24 documents |
| `eval/` | the question set and every result file |
| `tests/` | 10 test files |
| `check_apis.py` | one command that says what is broken |

`farmer/assistant.py` knows nothing about screens. Streamlit, WhatsApp and the
phone line all call the same `ask()`; each channel only converts its own message
format in and out. That is why adding a channel is small.

---

## Three things worth understanding before you change anything

**1. The council is not one model run three times.** Each of the three seats —
agronomist, farm economist, scheme officer — has its own remit, so the opinions
genuinely differ and agreement between them means something. A seat with nothing
to contribute replies `NO_INPUT` and is dropped from the count; a council where
everyone always talks is not a council. The agreement score is 70% the
chairman's number and 30% word overlap measured in `council/agreement.py` with
no model involved, so you can see when the chairman is flattering itself.

**2. Everything degrades instead of crashing.** A failed expert is marked
failed. One lone speaker skips the chairman. A dead council serves the plain
single-model answer. A missing Qdrant cluster falls back to a numpy index on
disk with the same RRF fusion. If a demo breaks, say which fallback fired — that
is the system working.

**3. Numbers are computed, not generated.** The spray window is worked out from
hourly wind and rain in `spray.py` and handed to the model already decided.
Asking a language model which hours are windy is inviting it to invent one.

---

## Results so far

**Retrieval** — 12 questions, each in all three languages, against 114 chunks.

The same-language boost was supposed to nudge evidence in the query's language
upward. It was added as a flat `+0.10` to RRF scores that run about 0.01–0.03,
so it was several times the entire spread: every same-language chunk outranked
every cross-language one regardless of relevance. A nudge on paper, a hard
language filter in practice — and it was switching off the cross-lingual
retrieval the project exists to demonstrate.

Three conditions, keyword recall:

| | en | hi | mr | mr MRR | mr same_lang |
|---|---|---|---|---|---|
| additive `+0.10` (the bug) | 0.46 | 0.33 | 0.33 | 0.74 | 1.00 |
| ratio `×1.10` | 0.46 | 0.55 | 0.48 | 0.76 | 0.71 |
| no boost (**shipped**) | 0.46 | **0.60** | **0.54** | **0.81** | 0.64 |

Fixing it helped. Removing it helped more. BGE-M3's shared vector space already
did the cross-lingual work; the heuristic on top only subtracted.

English is flat across all three, which is the control — 83% of the corpus is
English, so the boost is nearly a no-op there, and a harness that moved English
would be measuring something other than what it claims.

`same_lang` turns out to be a diagnostic, not a score to maximise: it falls
1.00 → 0.71 → 0.64 for Marathi *while recall climbs*. High `same_lang` means the
retriever was confined, not confident.

n = 12. The additive-versus-anything gap is far too large to be noise; ratio
versus off is suggestive, not settled.

**Generation** — not measured yet. Blocked on the Groq free tier, see below.

---

## Current state

| | status |
|---|---|
| Index | built, 114 chunks, committed so it deploys |
| Retrieval + ablation | done, three conditions in `eval/` |
| Council evaluation | **pending** — needs quota |
| Groq answers | working (`openai/gpt-oss-120b`) |
| Weather, geocoding, spray | working |
| SoilGrids | down upstream — fails everywhere, not our bug |
| data.gov.in prices | unreachable from our network; falls back to clearly-labelled samples |
| Twilio WhatsApp / IVR | written and tested offline, never run against live Twilio |
| Deployment | ready, not yet pushed |

### The quota ceiling

Groq's free tier allows 200,000 tokens per day. A full `--council both` run is
12 questions × 3 languages × 5 calls at roughly 3.4k tokens each — about 600k.
It cannot finish, and it fails two-thirds in having spent the whole day.

Run the scoped version instead:

```bat
python evaluate.py --council both --langs mr --limit 8
```

Marathi is where the claim lives, and 8 questions is a reportable n.

Note that `gpt-oss` is a reasoning model: it spends tokens thinking before it
writes, out of the same budget as the answer. That is why `GEN_MAX_TOKENS` is
2048 and `GROQ_REASONING_EFFORT` defaults to `low`. At a low ceiling the answer
can come back empty, and Devanagari suffers first, since the same answer costs
several times the tokens in Marathi that it does in English.

---

## Demoing it

Open the sidebar first and check it says `local` and 114 chunks.

Worth showing, in this order: the picture-first home screen in Marathi; asking
by tapping a card rather than typing; the Listen button (voice input without
voice output is half a bridge); the "How the council decided" panel; the daily
brief; and the Market tab.

Two practical notes.

**Set the village to Kochi before showing the spray window.** In clear weather
the rule engine rejects nothing and the advice is "06:00–19:00", which looks
like a rubber stamp. Same code, different forecast:

```
Nashik    28/28 hours good   ->  "Friday 06:00-19:00"      clear,  0 mm
Chennai   28/28 hours good   ->  "Friday 06:00-19:00"      clear,  3 mm
Kochi      5/28 hours good   ->  "Saturday 07:00-09:00"    drizzle, 44 mm
```

**Do not skip the Market tab because prices are samples.** "The government API
is unreachable and the system says so instead of inventing a price" is a better
moment than a working price would have been. The warning is the feature.

---

## Known limits — say these before anyone finds them

- The 24 documents in `data/` are illustrative, not real ICAR material. Several
  say so in their own first line. Fine for a demo; **not** fine for a farmer
  acting on a dose. Replace with real ICAR/KVK material and re-ingest before any
  real use.
- Keyword recall tops out around 0.46–0.60. Retrieval finds something relevant
  almost every time (`hit@k` 1.00) but only about half the expected facts.
  Chunking and `TOP_K` are the places to look.
- No crop-calendar or growth-stage logic. The profile stores crops, not sowing
  dates, so advice is not staged.
- The Twilio webhook has never run against Twilio's live servers.
- A public deployment spends our own Groq key on every visitor. No auth, no
  per-user rate limiting.
