"""convert_currency — today's FX rate, also not in any model's weights.

The budget note downstream ("is $100 a lot there?") must be grounded in the
rate this returns.

Free, keyless API: Frankfurter (European Central Bank rates).
https://www.frankfurter.app/
"""

from __future__ import annotations

import httpx

from pydantic_ai import ModelRetry
from schemas import Conversion

FX_URL = "https://api.frankfurter.dev/v1/latest"


async def convert_currency(amount: float, from_currency: str, to_currency: str) -> Conversion:
    """Convert an amount between two currencies at today's rate.

    Use this to judge how far the user's money goes at the destination.

    Args:
        amount: How much to convert, e.g. 100.
        from_currency: ISO code of the source currency, e.g. "USD".
        to_currency: ISO code of the destination currency, e.g. "EUR".
    """
    frm, to = from_currency.strip().upper(), to_currency.strip().upper()
    if frm == to:
        return Conversion(amount=amount, from_currency=frm, to_currency=to, rate=1.0, converted=amount)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(FX_URL, params={"amount": amount, "from": frm, "to": to})
        if resp.status_code != 200:
            raise ModelRetry(
                f"Couldn't convert {frm}->{to}. Check both are valid ISO codes (e.g. USD, EUR, JPY)."
            )
        data = resp.json()
        rates = data.get("rates") or {}
        if to not in rates:
            raise ModelRetry(f"No rate returned for {frm}->{to}. Are both valid ISO currency codes?")

    converted = rates[to]
    return Conversion(
        amount=amount,
        from_currency=frm,
        to_currency=to,
        rate=round(converted / amount, 6) if amount else 0.0,
        converted=converted,
    )
