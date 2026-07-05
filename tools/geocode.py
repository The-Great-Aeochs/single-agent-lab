"""geocode — the un-fakeable link in the chain.

This tool takes a city name and returns latitude/longitude. The model CANNOT
produce coordinates from its weights — it has to call this, observe the result,
and feed it to get_forecast. That is the whole lecture in one tool boundary:
"step N's input depends on step N-1's output."

Free, keyless API: Open-Meteo geocoding. https://open-meteo.com/
"""

from __future__ import annotations

import httpx

from pydantic_ai import ModelRetry
from schemas import LatLon

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


async def geocode(city: str) -> LatLon:
    """Resolve a city name to latitude/longitude.

    Call this BEFORE get_forecast — the forecast needs coordinates, not a name.

    Args:
        city: The city to locate, e.g. "Paris".
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(GEOCODE_URL, params={"name": city, "count": 1, "language": "en"})
        resp.raise_for_status()
        results = resp.json().get("results") or []

    if not results:
        # Type-valid string, business-invalid value → ModelRetry, not a crash.
        raise ModelRetry(
            f"No location found for {city!r}. Check the spelling, or try a more "
            f"specific name (e.g. 'Springfield, Illinois')."
        )

    top = results[0]
    label = ", ".join(
        part for part in (top.get("name"), top.get("admin1"), top.get("country_code")) if part
    )
    return LatLon(latitude=top["latitude"], longitude=top["longitude"], resolved_name=label)
