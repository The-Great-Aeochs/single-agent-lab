"""Run the agent and turn its message history into a ReAct trace.

This is what makes the loop *visible* — the three things the lab exists to show:
  • Thought      — the model's reasoning about what to do next (why a tool)
  • Action       — the tool call it decided on (name + arguments)
  • Observation  — the real result that comes back and feeds the next Thought
  • Final        — the validated, typed output

Pydantic AI hands us the whole history via `result.all_messages()`. We just walk
the parts and label them. The loop *is* the repetition of Action/Observation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from agent import LIMITS, agent
from schemas import NeedMoreInfo

# Guardrail / loop-limit exceptions we degrade gracefully instead of crashing on.
try:
    from pydantic_ai import UsageLimitExceeded
except Exception:  # pragma: no cover - import path varies by version
    from pydantic_ai.usage import UsageLimitExceeded  # type: ignore
try:
    from pydantic_ai.exceptions import UnexpectedModelBehavior
except Exception:  # pragma: no cover
    UnexpectedModelBehavior = ()  # type: ignore

GUARDRAIL_ERRORS = tuple(e for e in (UsageLimitExceeded, UnexpectedModelBehavior) if isinstance(e, type))


@dataclass
class Step:
    kind: str  # thought | action | observation | retry | final | error
    title: str
    body: str


def _args_str(part) -> str:
    """ToolCallPart.args may be a dict or a JSON string across versions."""
    if hasattr(part, "args_as_json_str"):
        try:
            return part.args_as_json_str()
        except Exception:
            pass
    args = getattr(part, "args", None)
    if isinstance(args, (dict, list)):
        return json.dumps(args)
    return str(args)


def run(query: str) -> tuple[list[Step], object, list[str]]:
    """Execute one agent run.

    Returns (trace steps, final output object, ordered list of tool names called).
    The tool-name sequence is what the evaluation scores.
    """
    try:
        result = agent.run_sync(query, usage_limits=LIMITS)
    except GUARDRAIL_ERRORS as e:
        # A guardrail (UsageLimits) or an exhausted retry budget fired. That is
        # the guardrail working — bound the blast radius. Degrade gracefully to
        # an abstention instead of crashing the app.
        out = NeedMoreInfo(
            question="Could you give a real, specific destination — a city or town?",
            reason=f"I couldn't resolve that place and stopped to avoid looping ({type(e).__name__}).",
        )
        return [Step("retry", "Guardrail stopped the run", str(e)),
                Step("final", "Final answer", repr(out))], out, []

    steps: list[Step] = []
    tool_sequence: list[str] = []

    for message in result.all_messages():
        for part in getattr(message, "parts", []):
            name = type(part).__name__
            if name in ("TextPart", "ThinkingPart"):
                body = (getattr(part, "content", "") or "").strip()
                if body:
                    steps.append(Step("thought", "Thought", body))
            elif name == "ToolCallPart":
                # Pydantic AI emits the structured output as a synthetic
                # `final_result_<Type>` tool call — that's the answer, not a
                # real tool. Skip it here; the Final row below already shows it.
                if part.tool_name.startswith("final_result"):
                    continue
                steps.append(Step("action", "Action", f"{part.tool_name}({_args_str(part)})"))
                tool_sequence.append(part.tool_name)
            elif name == "ToolReturnPart":
                if part.tool_name.startswith("final_result"):
                    continue
                steps.append(Step("observation", "Observation", f"{part.tool_name} → {part.content}"))
            elif name == "RetryPromptPart":
                body = getattr(part, "content", part)
                steps.append(Step("retry", "Retry (validation failed)", str(body)))

    output = getattr(result, "output", None)
    if output is None:
        output = getattr(result, "data", None)
    steps.append(Step("final", "Final answer", repr(output)))

    return steps, output, tool_sequence


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "What should I pack for the capital of France, and is $100 a lot there?"
    trace, output, seq = run(q)
    for s in trace:
        print(f"\n[{s.title}]\n{s.body}")
    print("\nTOOL SEQUENCE:", " -> ".join(seq) or "(none)")
