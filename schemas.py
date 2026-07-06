"""Typed contracts for the agent.

These Pydantic models are for type checking. Two kinds of validation types on them:

  1. Schema validation (automatic) — every type hint below becomes JSON Schema
     that the model must satisfy. Pydantic's SchemaValidator checks the model's
     tool arguments AND its final answer before your code ever runs.

  2. Business-logic validation (manual) — things a type can't express
     (`geocode("Pariss")` is a valid string but no such city) are caught by
     raising `ModelRetry(...)` inside a tool, or in an @agent.output_validator.

`LatLon` is produced by `geocode()` and consumed by `get_forecast()`. The model cannot invent a `LatLon` from its
weights, it has to call the tool, observe the result, and feed it forward.
That is "step N's input depends on step N-1's output," enforced by types.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LatLon(BaseModel):
    """A geocoded coordinate. Output of geocode(), input to get_forecast()."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    resolved_name: str = Field(description="What the geocoder actually matched, e.g. 'Paris, Île-de-France, FR'")


class Weather(BaseModel):
    """A current-conditions snapshot. The packing list must be derived from this."""

    temp_c: float
    condition: str
    wind_kph: float


class Conversion(BaseModel):
    """A currency conversion at today's rate. The budget note must be derived from this."""

    amount: float
    from_currency: str
    to_currency: str
    rate: float
    converted: float


# The final output is a UNION: succeed with a briefing, or ask for help.
# `output_type=[TravelBriefing, NeedMoreInfo]` lets the model return the other
# type when it cannot ground an answer in tool results. This is enforced by the type system, not by hope.


class TravelBriefing(BaseModel):
    """A grounded travel briefing. Every field must trace back to a tool result."""

    destination: str = Field(description="The city the briefing is about, as resolved by the tools")
    country: str | None = None
    weather: Weather
    local_currency: str = Field(description="ISO code of the destination's currency, e.g. EUR")
    budget_note: str = Field(description="Is the user's money a lot there? Grounded in the observed FX rate.")
    packing: list[str] = Field(description="Concrete items, justified by the observed weather")
    caveats: list[str] = Field(default_factory=list, description="Anything the tools could not confirm")


class NeedMoreInfo(BaseModel):
    """Return this INSTEAD of a briefing when the request can't be grounded.

    Unknown place, ambiguous country, a tool that kept failing — say so and ask,
    rather than fabricating a plausible-looking briefing.
    """

    question: str = Field(description="The one thing you need from the user to proceed")
    reason: str = Field(description="Why you could not answer from tool results alone")
