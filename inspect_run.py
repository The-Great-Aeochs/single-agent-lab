"""See the JSON, not just the trace.

Two things this prints, both straight from Pydantic AI:

  1) TOOL DEFINITIONS — the exact JSON schema (name + description + parameters)
     that gets sent to the model for each tool. You do NOT write this JSON or put
     tool descriptions in the system prompt: Pydantic AI generates it from each
     tool's Python signature + docstring. This is the "tools as JSON" from the
     lecture, produced automatically from the code.

  2) RAW MESSAGES — the full conversation as JSON: the system prompt, the user
     turn, every assistant tool call (tool_name + args + tool_call_id), every
     tool return, and the final structured output. This is the model's actual
     tool-calling output, underneath the pretty trace panel.

Run:  python inspect_run.py "Pack for a trip to Tokyo."

Bonus — the literal HTTP request/response on the wire (the provider's own JSON):
      OPENAI_LOG=debug python inspect_run.py "Pack for a trip to Tokyo."
"""

from __future__ import annotations

import json
import sys

from agent import LIMITS, agent


def tool_definitions() -> list[dict]:
    """The JSON tool schema sent to the model — generated from signatures + docstrings."""
    defs = []
    for tool in agent._function_toolset.tools.values():
        td = tool.tool_def
        defs.append(
            {
                "name": td.name,
                "description": td.description,
                "parameters": td.parameters_json_schema,
            }
        )
    return defs


def main() -> None:
    query = " ".join(sys.argv[1:]) or "Pack for a trip to Tokyo."

    print("=" * 72)
    print("1) TOOL DEFINITIONS  (the JSON the model sees — auto-generated from code)")
    print("=" * 72)
    print(json.dumps(tool_definitions(), indent=2))

    print("\n" + "=" * 72)
    print(f"2) RAW MESSAGES  (model's actual tool calls + returns)   query: {query!r}")
    print("=" * 72)
    result = agent.run_sync(query, usage_limits=LIMITS)
    messages = json.loads(result.all_messages_json())  # bytes -> Python -> pretty
    print(json.dumps(messages, indent=2, default=str))


if __name__ == "__main__":
    main()
