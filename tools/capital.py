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
    """OPTIONAL shortcut: return the capital city of a country.

    You do NOT have to use this — for a state, region, city, or landmark, pick a
    city yourself and call geocode on it directly. This only helps for a bare
    country name where you want its capital as a representative city.

    Args:
        country: The country name, e.g. "France".
    """
    key = country.strip().lower()
    if key not in CAPITALS:
        raise ModelRetry(
            f"{country!r} isn't in my small country table. Pick a representative "
            f"city for it yourself (e.g. a state's main city) and geocode that "
            f"directly — don't stop to ask the user."
        )
    return CAPITALS[key]
