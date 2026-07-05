# Single-Agent Lab — Travel Briefing Agent

A teaching build for **Week 5: Single-Agent Systems**. One LLM, four tools, and a
loop — assembled so the whole agent is visible in a few files, and so a single
run *demonstrates* the lecture instead of hiding it.

> **The claim we're paying off:** any task where step N's input depends on step
> N-1's output needs the model to see the result before deciding what's next.
> That's the mechanical justification for `agent = LLM + tools + loop`.

## The use-case

Type **anything** as a destination — a city, a state, a country, a landmark. The
agent turns it into a concrete place, looks up **today's** weather and exchange
rate, and decides what to pack and whether your money goes far — none of which is
in the model's weights.

```
"Plan a trip to Meghalaya on a ~10k budget"

💭 Thought   Meghalaya is a state — its main city is Shillong. I'll look that up.
🔧 Action    geocode("Shillong")            → { lat: 25.57, lon: 91.88 }   ← un-fakeable
💭 Thought   get_forecast needs THOSE coords
🔧 Action    get_forecast(25.57, 91.88)     → 22°C, overcast
🔧 Action    convert_currency(10000, INR..) → grounds the budget note
✅ Final     TravelBriefing(...)            ← validated Pydantic object
```

`get_forecast` takes **latitude/longitude, not a city** — so the model *cannot*
shortcut it from memory. It has to call `geocode`, observe the coordinates, and
feed them forward. That forced link is the lecture, live.

Notice the division of labour: the model uses **its own knowledge** to turn free
text (a state, a country, a landmark) into a concrete city to geocode — that
static disambiguation is fine to do from memory. What it must **not** invent is
the dynamic, tool-only part: coordinates, today's weather, today's rate.
`get_capital` is an *optional* shortcut for a bare country name, **not** a
required step — the geocoder resolves cities, the model resolves the rest. (This
is why typing a non-country like *Meghalaya* works instead of dead-ending.)

## What each lecture idea maps to

| Lecture idea | Where it lives |
|---|---|
| Thought → Action → Observation loop | the trace panel in `app.py`, built from `trace.py` |
| Tool calling (model decides + tool responds) | `tools/*.py`, called by the model, executed by us |
| Structured output | `TravelBriefing` in `schemas.py`, via `output_type=` |
| Schema validation (automatic) | type hints on tools and output → JSON Schema |
| Business-logic validation (manual) | `ModelRetry(...)` in tools; `@agent.output_validator` |
| Per-tool retry budgets | `agent.tool_plain(retries=N)` in `agent.py` |
| Guardrails (bound the loop) | `UsageLimits(...)` in `agent.py` |
| Graceful degradation when a guardrail fires | `trace.py` catches it → returns `NeedMoreInfo`, never crashes |
| Fail, don't hallucinate | `output_type=[TravelBriefing, NeedMoreInfo]` union |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # then add your key
```

Provider is **OpenAI** by default (`openai:gpt-4.1`); Pydantic AI reads
`OPENAI_API_KEY` from `.env` automatically. To use Anthropic instead, set
`ANTHROPIC_API_KEY` and `AGENT_MODEL=anthropic:claude-opus-4-8`.

The tools use **free, keyless** APIs (Open-Meteo for geocode + forecast,
Frankfurter for FX), so only the model needs a key.

## Run

```bash
python app.py                 # Gradio UI with the live trace panel
python examples.py            # the three canonical queries in the terminal
python trace.py "Pack for Tokyo"   # one query, printed trace
python eval/run_eval.py       # score the agent
```

## Evaluation

A workflow's tool order is fixed in code, so it's trivially correct. An agent
*chooses* its order at runtime — so whether it took the right path is a real,
measurable thing. `eval/run_eval.py` ships two metrics:

- **output_type_accuracy** — `TravelBriefing` vs `NeedMoreInfo`, as expected.
- **dependency_respected** — did `geocode` come **before** `get_forecast`? The
  single most important ordering in this agent.

It **also prints the actual tool calls per case** and leaves a stubbed
`tool_sequence_accuracy()` for you to implement (see Assignment 1). Add or edit
cases in `eval/cases.json`.

## Assignments

1. **Implement tool-sequence accuracy.** `eval/run_eval.py` has a stubbed
   `tool_sequence_accuracy(actual, expected)` that currently raises
   `NotImplementedError`. Implement it — and don't stop at one metric. Try an
   **LCS-based** score (`longest common subsequence / len(expected)`, partial
   credit), a strict **exact-match** rate, a normalized **edit-distance**
   (Levenshtein) score, and an **efficiency** score (`len(expected) /
   len(actual)`, penalizing wasted calls). Wire them into the per-case table and
   the aggregate, then discuss when each lens is the right one — especially for
   the abstention cases, where `expected_sequence` is `[]` but the model may
   still probe a tool before giving up.
2. **Add a dynamic destination tool.** Give the agent a `web_search`-style tool
   and a query like *"pack for the capital of the next Olympics host."* Score
   whether it uses the new tool **only when needed** — and whether the identical
   downstream `geocode → get_forecast` chain still runs.
3. **Break the chain on purpose.** Remove the "`get_forecast` needs coordinates"
   rule from the system prompt and re-run the eval. Watch `dependency_respected`
   fall. Explain, in terms of the lecture, why the type of `get_forecast`'s
   argument is doing more work than the prompt.
4. **Kill the last hardcoded table.** `tools/capital.py` is a ~45-entry
   country→capital dict — it can't handle states, regions, or landmarks, and it's
   now redundant since the model resolves places itself before geocoding. Remove
   `get_capital` entirely, drop it from `agent.py`, and confirm the eval still
   passes. Then discuss: what did the tool actually buy us, and when *is* a static
   lookup tool worth building versus letting the model decide?
