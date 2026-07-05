"""Evaluate the agent — with tool-sequence accuracy front and center.

A workflow's tool order is fixed in code, so it's trivially "correct." An agent
*chooses* its order at runtime, so whether it took the right path is a real,
measurable thing. That is what we score here.

Metrics per case:
  • output_type_correct  — did it return TravelBriefing vs NeedMoreInfo as expected?
  • sequence_accuracy    — order-aware overlap between the tools it called and the
                           expected sequence (LCS / len(expected)). Partial credit:
                           getting geocode→forecast right still scores even if it
                           adds an extra call.
  • exact_sequence       — did the tool order match exactly?
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


def lcs_len(a: list[str], b: list[str]) -> int:
    """Longest common subsequence length — order-aware overlap."""
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) - 1, -1, -1):
        for j in range(len(b) - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if a[i] == b[j] else max(dp[i + 1][j], dp[i][j + 1])
    return dp[0][0]


def sequence_accuracy(actual: list[str], expected: list[str]) -> float:
    """1.0 = expected order fully present (extra calls don't help but don't erase it)."""
    if not expected:
        return 1.0 if not actual else 0.0  # expected no tools; any call is a miss
    return lcs_len(actual, expected) / len(expected)


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
            _, output, seq = run(c["query"])
            got_type = type(output).__name__
        except Exception as e:
            rows.append({"id": c["id"], "error": f"{type(e).__name__}: {e}"})
            continue

        expected = c["expected_sequence"]
        rows.append(
            {
                "id": c["id"],
                "type_ok": got_type == c["expected_output"],
                "seq_acc": sequence_accuracy(seq, expected),
                "exact": seq == expected,
                "dep_ok": dependency_respected(seq, expected),
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
            f"({r['got_type']:<13}) seq_acc={r['seq_acc']:.2f} "
            f"exact={'y' if r['exact'] else 'n'} dep={dep}\n"
            f"                   calls: {r['seq']}"
        )

    scored = [r for r in rows if "error" not in r]
    if scored:
        type_acc = sum(r["type_ok"] for r in scored) / len(scored)
        seq_acc = sum(r["seq_acc"] for r in scored) / len(scored)
        deps = [r["dep_ok"] for r in scored if r["dep_ok"] is not None]
        dep_acc = (sum(deps) / len(deps)) if deps else float("nan")
        print("\n=== Aggregate ===")
        print(f"  output_type_accuracy   {type_acc:.2f}")
        print(f"  tool_sequence_accuracy {seq_acc:.2f}   <-- the agent-vs-workflow metric")
        print(f"  dependency_respected   {dep_acc:.2f}")


if __name__ == "__main__":
    main()
