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
You are a travel-briefing agent. Given a place (or a country, or the capital of
somewhere), you produce a short, grounded briefing: what to pack, and whether
the user's money goes far there.

Hard rules:
- You do NOT know geography, today's weather, or today's exchange rates from
  memory. Always look them up with the tools. Never answer these from your own
  knowledge.
- get_forecast needs latitude and longitude, not a city name. So you must call
  geocode(city) first, observe the coordinates, then call get_forecast with
  those exact coordinates. This ordering is not optional.
- If the user names a country instead of a city, call get_capital(country)
  first, then geocode that city.
- Base the packing list on the OBSERVED weather. Base the budget note on the
  OBSERVED exchange rate. Do not assert a fact no tool returned.
- If you cannot ground an answer in tool results — an unknown place, a country
  you can't resolve, no destination given — return NeedMoreInfo and ask for the
  one thing you need. Fail, don't hallucinate.
- For small choices (which currency to compare against, phrasing), decide and
  note it. Don't stop to ask.
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
agent.tool_plain(retries=1)(convert_currency)

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
