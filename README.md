# Single-Agent Lab — Travel Briefing Agent

A small teaching agent for **Week 5: Single-Agent Systems**. One LLM + four tools
+ a loop. Ask for a travel briefing about any place; it resolves the place, looks
up today's weather and exchange rate, and returns a validated result — or asks
for more info instead of hallucinating.

The point: `get_forecast` needs coordinates, so the model **must** call `geocode`
first and feed the result forward — a dependent chain it decides at runtime, not
a fixed pipeline.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # add OPENAI_API_KEY
```

OpenAI by default (`openai:gpt-4.1`); switch with `ANTHROPIC_API_KEY` +
`AGENT_MODEL=anthropic:claude-opus-4-8`. Tools use free, keyless APIs — only the
model needs a key.

## Run

```bash
python app.py                            # Gradio UI: live trace + Raw JSON panel
python examples.py                       # three canonical queries
python trace.py "Pack for Tokyo"         # one query, printed trace
python inspect_run.py "Pack for Tokyo"   # tool schemas + raw model JSON
python eval/run_eval.py                  # score the agent
```

## Layout

| file | what |
|---|---|
| `agent.py` | the agent: model, system prompt, the four `tool_plain(...)` registrations, `UsageLimits` |
| `schemas.py` | typed output (`TravelBriefing` \| `NeedMoreInfo`) + tool types |
| `tools/` | `web_search`, `geocode`, `get_forecast`, `convert_currency` |
| `trace.py` | runs the agent, labels the Thought → Action → Observation loop |
| `app.py` | Gradio UI (dark theme) |
| `inspect_run.py` | dump the tool-definition JSON + raw messages |
| `eval/` | test cases + scorer |

Tool descriptions live in the JSON schema — auto-generated from docstrings + type
hints, not written in the system prompt. See them with `inspect_run.py`.

## Assignments

1. Implement `tool_sequence_accuracy()` in `eval/run_eval.py` (LCS / exact-match / edit-distance / efficiency).
2. Read about these specific code blobs from smol agents repo 
  a. File: agents.py, MultiStepAgent._run_stream, lines ~540-610.

  b. File: agents.py, MultiStepAgent.write_memory_to_messages, lines ~758-770. (list of steps becomes the list of messages sent to the model)
  
  c. File: agents.py, ToolCallingAgent._step_stream, lines ~1276-1360. (one full Thought-Action step for the JSON format)
