"""The agent — the whole thing, in one readable file.

This is the point of the lab: the entire agent is visible here. An LLM, four
tools, a typed output, and a bound on the loop. Nothing is hidden.

    agent = LLM + tools + loop
            (model) (below) (Pydantic AI runs it)

Provider: OpenAI. Pydantic AI is provider-agnostic — it reads OPENAI_API_KEY
from the environment automatically. Change AGENT_MODEL to point elsewhere.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.usage import UsageLimits

load_dotenv()  # pull OPENAI_API_KEY / ANTHROPIC_API_KEY / AGENT_MODEL from .env

from schemas import NeedMoreInfo, TravelBriefing
from tools.capital import get_capital
from tools.currency import convert_currency
from tools.geocode import geocode
from tools.weather import get_forecast

# OpenAI by default. Swap to e.g. "openai:gpt-5.1" or "anthropic:claude-opus-4-8".
MODEL = os.getenv("AGENT_MODEL", "openai:gpt-4.1")

SYSTEM_PROMPT = """\
You are a travel-briefing agent. Given ANYTHING a user names as a destination —
a city, a state or region, a country, a landmark, or a loose description — you
produce a short, grounded briefing: what to pack, and how far their money goes.

Turning free text into a place you can look up:
- You MAY use your own knowledge to choose a specific CITY to look up. If the
  user names a state or region, pick its main/representative city (e.g. Meghalaya
  -> Shillong); for a bare country, a major city; for a landmark, the city it's
  in. Say which city you chose and why.
- The geocoder only knows cities and towns — it will NOT resolve a state, a
  region, or a landmark. So resolve those to a city yourself first, then geocode
  the city.

The one thing you must NOT do from memory:
- You may pick the city, but you may NOT invent its coordinates, today's weather,
  or today's exchange rate. Those are dynamic and unknowable — always get them
  from the tools. get_forecast needs latitude/longitude, so call geocode(city)
  first and forecast the coordinates it returns.

Other rules:
- Resolve the destination FIRST with geocode. If it won't resolve to a real city,
  return NeedMoreInfo right away — do NOT try to look up the weather or currency
  of a place you couldn't find.
- get_capital(country) is an OPTIONAL shortcut for a bare country name. You don't
  need it — picking a city yourself and geocoding it works just as well.
- Base packing on the OBSERVED weather; base the budget note on the OBSERVED
  exchange rate. If an amount has no currency, state the assumption you make
  (e.g. the destination's local currency) instead of stalling.
- If geocode can't find your chosen city, try at most ONE alternative (a different
  spelling, or a nearby major city). If that also fails, return NeedMoreInfo — do
  NOT keep calling geocode on a place that won't resolve.
- Return NeedMoreInfo only when there is genuinely no destination to work with,
  or nothing you can resolve — never merely because a name wasn't in a lookup
  table. Fail (ask), don't hallucinate.
- For small choices, decide and note it. Don't stop to ask.
"""

# One LLM, one typed output that is a UNION (succeed, or ask for help).
agent = Agent(
    MODEL,
    output_type=[TravelBriefing, NeedMoreInfo],
    system_prompt=SYSTEM_PROMPT,
)

# The four tools. Each gets its OWN retry budget: when a tool raises ModelRetry
# or the model sends type-invalid arguments, only that tool's counter advances.
# This is separate from the run-wide UsageLimits below.
agent.tool_plain(retries=1)(get_capital)
agent.tool_plain(retries=2)(geocode)
agent.tool_plain(retries=1)(get_forecast)
agent.tool_plain(retries=2)(convert_currency)

# Guardrail: bound the loop. UsageLimits caps TOTAL work in a single run, so a
# fan-out request ("plan a 5-country trip") can't spiral into 40 tool calls.
# Different governor from per-tool `retries` above.
LIMITS = UsageLimits(request_limit=6, tool_calls_limit=10)


@agent.output_validator
def briefing_is_grounded(ctx: RunContext, output: TravelBriefing | NeedMoreInfo):
    """Output-side business-logic validation — the twin of ModelRetry-in-a-tool.

    Schema validation already guaranteed the shape. This checks something a type
    can't: a briefing must actually name a destination. Raising ModelRetry here
    sends the model back around the loop with the reason, spending the *output*
    retry budget (separate from the per-tool budgets above).
    """
    if isinstance(output, TravelBriefing) and not output.destination.strip():
        raise ModelRetry("The briefing has no destination — resolve the city with the tools first.")
    return output
