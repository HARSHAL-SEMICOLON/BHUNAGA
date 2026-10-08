# Tests

```bash
pytest tests/ -v          # 279 tests, all pass offline
```

Nothing here touches the network or needs an API key. Every outside service —
Groq, Qdrant, data.gov.in, Open-Meteo, SoilGrids, Twilio — is replaced with a
canned response, which is the only way to test the cases that actually break in
the field: a 200 with zero records, a renamed column, a rate limit, a cluster
that answers 404.

| Suite | Style | What it checks |
|---|---|---|
| `test_whitebox.py` | white-box | internal branches and logic |
| `test_blackbox.py` | black-box | CLI and data contracts via subprocess |
| `test_units.py` | unit | individual functions across the package |
| `test_integration.py` | end-to-end | full retrieval pipeline, in memory |
| `test_council.py` | unit + flow | the three experts, the chairman, every failure path |
| `test_local_store.py` | unit | the local index, the Qdrant fallback, the question bank |
| `test_apis.py` | mocked I/O | prices, weather, spray window, soil, geocoding |
| `test_languages.py` | contract | the interface really works in all three languages |
| `test_gaps.py` | regression | every gap found in the audit, so it cannot come back |

## What the newer suites are for

**`test_council.py`** — the interesting cases are the ugly ones. A chairman that
ignores the JSON instruction and writes prose. An expert that rate-limits. Every
expert abstaining. Those are what happens on a Friday afternoon on the free
tier, and the app has to survive all of them without showing a farmer a stack
trace.

**`test_apis.py`** — the price tests matter most. The bug that made this app
quietly serve sample prices was not a crash: data.gov.in returned HTTP 200 and
an empty list because the filter was spelled the way an older version of the API
wanted. So the client is fed every plausible API shape — four filter spellings,
three column-naming conventions — and has to find the data in each.

**`test_languages.py`** — it is easy to ship a "trilingual" app where the answers
are translated and every button still says Calculate. These tests fail the build
if any string is missing a translation, if a screen does not use the translation
layer, or if a screen keeps its own translation table. One case per screen per
language is what catches a screen someone forgot to wire up.

**`test_gaps.py`** — each test corresponds to a gap found in the audit. Several
check facts about the repository itself: that the knowledge base really is
multilingual, that `farmer_profile.json` is gitignored, that the Streamlit floor
is high enough for `st.audio_input`. Those decay silently without a test.

## Conventions

- No network, no API key, no model download
- Failure paths are tested as carefully as success paths
- Where a test encodes a real bug, the docstring says which one
