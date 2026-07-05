"""web_search — look up ANY place on the open web. No hardcoded tables.

This replaces the old get_capital lookup dict. Instead of a static ~45-country
table (which dead-ended on states, regions, and landmarks), the agent can search
the web for whatever the user typed: a region's main city, an obscure town, or
"is this even a real place?" before planning a trip.

Keyless: DuckDuckGo via the `ddgs` package.
"""

from __future__ import annotations

from ddgs import DDGS

from pydantic_ai import ModelRetry


def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for anything.

    Use this to resolve or verify a place the user names — find a state's or
    region's main city, disambiguate a name, or check whether a place is real
    before planning a trip. Return the top results as text; read them and decide
    what to do next.

    Args:
        query: What to search for, e.g. "main city of Meghalaya" or
            "is Zorbania a real country".
        max_results: How many results to return (default 5).
    """
    try:
        results = list(DDGS().text(query, max_results=max_results))
    except Exception as e:
        # Transient (rate limit, network) — let the model retry or rephrase.
        raise ModelRetry(f"Web search failed ({type(e).__name__}). Try again or rephrase the query.")

    if not results:
        return f"No web results for {query!r}."
    return "\n".join(f"- {r.get('title', '')}: {r.get('body', '')}" for r in results)
