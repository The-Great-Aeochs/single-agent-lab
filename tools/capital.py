"""get_capital — a deliberately local lookup.

Backed by a small table, not the internet. The system prompt tells the model it
does NOT know geography and must look it up here. That turns the lecture's
weakness ("the model half-knows capitals") into a teaching feature: you can show
grounding beating parametric recall — and show what a ModelRetry looks like when
the country isn't on file.
"""

from __future__ import annotations

from pydantic_ai import ModelRetry

CAPITALS: dict[str, str] = {
    "france": "Paris",
    "japan": "Tokyo",
    "italy": "Rome",
    "spain": "Madrid",
    "germany": "Berlin",
    "portugal": "Lisbon",
    "greece": "Athens",
    "netherlands": "Amsterdam",
    "belgium": "Brussels",
    "austria": "Vienna",
    "switzerland": "Bern",
    "norway": "Oslo",
    "sweden": "Stockholm",
    "denmark": "Copenhagen",
    "finland": "Helsinki",
    "ireland": "Dublin",
    "poland": "Warsaw",
    "czechia": "Prague",
    "hungary": "Budapest",
    "iceland": "Reykjavik",
    "united kingdom": "London",
    "uk": "London",
    "united states": "Washington",
    "usa": "Washington",
    "canada": "Ottawa",
    "mexico": "Mexico City",
    "brazil": "Brasília",
    "argentina": "Buenos Aires",
    "india": "New Delhi",
    "china": "Beijing",
    "south korea": "Seoul",
    "thailand": "Bangkok",
    "vietnam": "Hanoi",
    "indonesia": "Jakarta",
    "australia": "Canberra",
    "new zealand": "Wellington",
    "egypt": "Cairo",
    "morocco": "Rabat",
    "south africa": "Pretoria",
    "kenya": "Nairobi",
    "turkey": "Ankara",
    "united arab emirates": "Abu Dhabi",
    "uae": "Abu Dhabi",
}


def get_capital(country: str) -> str:
    """Return the capital city of a country.

    Call this when the user names a country rather than a city — you must look
    the capital up here, not recall it from memory.

    Args:
        country: The country name, e.g. "France".
    """
    key = country.strip().lower()
    if key not in CAPITALS:
        raise ModelRetry(
            f"I don't have the capital of {country!r} on file. "
            f"Ask the user for the specific city instead of guessing."
        )
    return CAPITALS[key]
