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
# Tool-sequence metrics.
#
# `trace.run()` returns the ordered list of tool names the agent actually
# called; each case carries the `expected_sequence`. These four lenses each
# answer a different question about the overlap. None is "the" metric — they
# disagree most sharply on the abstention cases (expected == []), which is
# exactly why we report all four.
#
#   tool_sequence_accuracy  LCS(actual, expected) / len(expected)
#       "Of the ordered path I was supposed to walk, how much did I walk, in
#        order?"  Rewards following the right chain; blind to *extra* calls, so
#        it must be read alongside `efficiency`. This is the headline metric:
#        for a dependent-chain agent, walking the required order is the point.
#
#   exact_match             1.0 iff actual == expected, else 0.0
#       Strictest lens. The only one that fails a run for a single wasted call
#       or a reordering. Right when the sequence is a contract, not a goal.
#
#   edit_similarity         1 - levenshtein(actual, expected) / max(len, len)
#       Symmetric: one number that penalizes BOTH missing and extra calls,
#       weighting each insert/delete/substitute equally. The balanced default
#       when you care about "how far off" rather than "did it nail it".
#
#   efficiency              len(expected) / len(actual), capped at 1.0
#       Ignores order entirely — purely "did it waste calls?". A run can have
#       perfect LCS accuracy and terrible efficiency (right path + detours).
#
# Abstention (expected == []): the right move is to call *nothing*. There is no
# ordered path to recover, so LCS accuracy and edit_similarity both collapse to
# a clean binary (1.0 iff the agent also called nothing). Efficiency does too.
# But the lenses part ways on a *probe-then-give-up* run — say the model
# geocodes "Zorbania", gets nothing, and abstains: every lens here scores it
# 0.0 because a call was made, whereas a "did it reach the right OUTPUT" view
# would forgive it. We deliberately score the trace, not the intent — a wasted
# call is a wasted call — but that divergence is the point worth arguing about.
# ---------------------------------------------------------------------------
def _lcs_len(a: list[str], b: list[str]) -> int:
    """Length of the longest common subsequence (order-preserving, not contiguous)."""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for x in a:
        curr = [0]
        for j, y in enumerate(b):
            curr.append(prev[j] + 1 if x == y else max(prev[j + 1], curr[j]))
        prev = curr
    return prev[-1]


def _levenshtein(a: list[str], b: list[str]) -> int:
    """Edit distance between two token sequences (insert/delete/substitute = 1)."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        curr = [i]
        for j, y in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = curr
    return prev[-1]


def tool_sequence_accuracy(actual: list[str], expected: list[str]) -> float:
    """Headline metric: fraction of the expected ordered path recovered, via LCS.

    LCS(actual, expected) / len(expected). Order-sensitive (a swap lowers the
    score) but forgiving of extra calls — pair it with `efficiency` to catch
    detours. When nothing was expected, a perfect score means the agent also
    called nothing.
    """
    if not expected:
        return 1.0 if not actual else 0.0
    return _lcs_len(actual, expected) / len(expected)


def exact_match(actual: list[str], expected: list[str]) -> float:
    """1.0 iff the sequences are identical, order and all."""
    return 1.0 if actual == expected else 0.0


def edit_similarity(actual: list[str], expected: list[str]) -> float:
    """Normalized Levenshtein similarity: 1 - dist / max(len). Symmetric."""
    denom = max(len(actual), len(expected))
    if denom == 0:
        return 1.0
    return 1.0 - _levenshtein(actual, expected) / denom


def efficiency(actual: list[str], expected: list[str]) -> float:
    """len(expected) / len(actual), capped at 1.0. Order-blind; flags wasted calls."""
    if not actual:
        return 1.0 if not expected else 0.0
    return min(1.0, len(expected) / len(actual))


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

        exp = c["expected_sequence"]
        rows.append(
            {
                "id": c["id"],
                "type_ok": got_type == c["expected_output"],
                "dep_ok": dependency_respected(seq, exp),
                "lcs": tool_sequence_accuracy(seq, exp),
                "exact": exact_match(seq, exp),
                "edit": edit_similarity(seq, exp),
                "eff": efficiency(seq, exp),
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
            f"                   seq: lcs={r['lcs']:.2f} exact={r['exact']:.0f} "
            f"edit={r['edit']:.2f} eff={r['eff']:.2f}\n"
            f"                   calls: {r['seq']}"
        )

    scored = [r for r in rows if "error" not in r]
    if scored:
        type_acc = sum(r["type_ok"] for r in scored) / len(scored)
        deps = [r["dep_ok"] for r in scored if r["dep_ok"] is not None]
        dep_acc = (sum(deps) / len(deps)) if deps else float("nan")
        n = len(scored)
        print("\n=== Aggregate ===")
        print(f"  output_type_accuracy   {type_acc:.2f}")
        print(f"  dependency_respected   {dep_acc:.2f}")
        print(f"  tool_sequence_accuracy {sum(r['lcs'] for r in scored) / n:.2f}  (LCS / len(expected))")
        print(f"  exact_match_rate       {sum(r['exact'] for r in scored) / n:.2f}")
        print(f"  edit_similarity        {sum(r['edit'] for r in scored) / n:.2f}")
        print(f"  efficiency             {sum(r['eff'] for r in scored) / n:.2f}")


if __name__ == "__main__":
    main()
