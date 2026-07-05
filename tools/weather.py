"""get_forecast — inherently dynamic. Today's weather is in no model's weights.

Consumes the coordinates that geocode() produced. The packing list downstream
must follow from what this returns — an observation the model could not have
pre-planned.

Free, keyless API: Open-Meteo forecast. https://open-meteo.com/
"""

from __future__ import annotations

import httpx

from pydantic_ai import ModelRetry
from schemas import Weather

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# A readable subset of WMO weather codes.
WMO: dict[int, str] = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "light rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "light snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
}


async def get_forecast(latitude: float, longitude: float) -> Weather:
    """Get current weather at a latitude/longitude.

    Requires coordinates from geocode() — this tool does not accept a city name.

    Args:
        latitude: Degrees north, from geocode().
        longitude: Degrees east, from geocode().
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                FORECAST_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "temperature_2m,weather_code,wind_speed_10m",
                },
            )
            resp.raise_for_status()
            current = resp.json()["current"]
    except httpx.HTTPError as e:
        # Transient (5xx, timeout, network). Let the model retry rather than crash.
        raise ModelRetry(f"Weather service is temporarily unavailable ({type(e).__name__}). Try again.")

    return Weather(
        temp_c=current["temperature_2m"],
        condition=WMO.get(current["weather_code"], f"code {current['weather_code']}"),
        wind_kph=current["wind_speed_10m"],
    )
