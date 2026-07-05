"""The three canonical queries — one per teaching point.

Run:  python examples.py           (all three)
      python examples.py 1         (just the first)
"""

from __future__ import annotations

import sys

from trace import run

QUERIES = {
    "1 · dependent chain": (
        "What should I pack for the capital of France, and is $100 a lot there?"
    ),
    "2 · model-chosen fan-out": (
        "I'm deciding between Tokyo and Lisbon this week — pack for whichever is warmer."
    ),
    "3 · honest abstention": (
        "What should I pack for my trip?"  # no destination → should ask, not guess
    ),
}


def show(label: str, query: str) -> None:
    print("=" * 70)
    print(f"{label}\nQ: {query}\n")
    trace, output, seq, _ = run(query)
    for s in trace:
        print(f"  [{s.title}] {s.body}")
    print(f"\n  TOOL SEQUENCE: {' -> '.join(seq) or '(none)'}")
    print(f"  OUTPUT TYPE:   {type(output).__name__}\n")


if __name__ == "__main__":
    items = list(QUERIES.items())
    if len(sys.argv) > 1:
        idx = int(sys.argv[1]) - 1
        label, query = items[idx]
        show(label, query)
    else:
        for label, query in items:
            show(label, query)
