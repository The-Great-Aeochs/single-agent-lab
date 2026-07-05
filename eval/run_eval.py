"""Evaluate the agent.

A workflow's tool order is fixed in code, so it's trivially "correct." An agent
*chooses* its order at runtime — so whether it took the right path is a real,
measurable thing. This harness ships two metrics and leaves the headline one to
you (see the ASSIGNMENT below).

Ships:
  • output_type_correct  — did it return TravelBriefing vs NeedMoreInfo as expected?
  • dependency_respected — for cases with both, did geocode come BEFORE get_forecast?
                           (the single most important ordering in this agent)

Run:  python eval/run_eval.py
"""

from __future__ import annotations

import json
import os
import sys

# Allow "python eval/run_eval.py" from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trace import run  # noqa: E402

CASES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases.json")


# ---------------------------------------------------------------------------
# ASSIGNMENT — implement `tool_sequence_accuracy` yourself.
#
# This harness scores output type and the geocode->get_forecast dependency, but
# it deliberately does NOT score how well the whole tool *sequence* matched the
# expected one. That's your task.
#
# You have everything you need: each case in cases.json carries an
# `expected_sequence`, and every run returns the actual `tool_sequence` from
# `trace.run()`. Implement a metric (or several) that scores the ordered overlap,
# then wire it into the per-case table and the aggregate below. Ideas:
#   • LCS-based accuracy   — longest common subsequence / len(expected)
#   • exact-match rate     — did the order match exactly?
#   • edit distance        — normalized Levenshtein over the two sequences
#   • efficiency           — len(expected) / len(actual), penalizing wasted calls
# Then argue when each lens is the right one — especially for the abstention
# cases, where `expected_sequence` is [] but the model may still probe a tool
# before deciding to give up.
# ---------------------------------------------------------------------------
def tool_sequence_accuracy(actual: list[str], expected: list[str]) -> float:
    raise NotImplementedError("ASSIGNMENT: implement a tool-sequence-accuracy metric here.")


def dependency_respected(actual: list[str], expected: list[str]) -> bool | None:
    """None when the pair isn't part of this case; else True/False."""
    if "geocode" not in expected or "get_forecast" not in expected:
        return None
    if "geocode" not in actual or "get_forecast" not in actual:
        return False
    return actual.index("geocode") < actual.index("get_forecast")


def main() -> None:
    with open(CASES) as f:
        cases = json.load(f)

    rows = []
    for c in cases:
        try:
            _, output, seq, _ = run(c["query"])
            got_type = type(output).__name__
        except Exception as e:
            rows.append({"id": c["id"], "error": f"{type(e).__name__}: {e}"})
            continue

        rows.append(
            {
                "id": c["id"],
                "type_ok": got_type == c["expected_output"],
                "dep_ok": dependency_respected(seq, c["expected_sequence"]),
                "got_type": got_type,
                "seq": " -> ".join(seq) or "(none)",
            }
        )

    print("\n=== Per-case ===")
    for r in rows:
        if "error" in r:
            print(f"  {r['id']:<16} ERROR: {r['error']}")
            continue
        dep = {True: "yes", False: "NO", None: "-"}[r["dep_ok"]]
        print(
            f"  {r['id']:<16} type={'ok' if r['type_ok'] else 'MISS'} "
            f"({r['got_type']:<13}) dep={dep}\n"
            f"                   calls: {r['seq']}"
        )

    scored = [r for r in rows if "error" not in r]
    if scored:
        type_acc = sum(r["type_ok"] for r in scored) / len(scored)
        deps = [r["dep_ok"] for r in scored if r["dep_ok"] is not None]
        dep_acc = (sum(deps) / len(deps)) if deps else float("nan")
        print("\n=== Aggregate ===")
        print(f"  output_type_accuracy   {type_acc:.2f}")
        print(f"  dependency_respected   {dep_acc:.2f}")
        print(f"  tool_sequence_accuracy (ASSIGNMENT — implement tool_sequence_accuracy())")


if __name__ == "__main__":
    main()
