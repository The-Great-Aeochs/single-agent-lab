"""Gradio UI — the trace panel is the whole point.

The left column is the ReAct loop made visible: Thought / Action / Observation
rows in the same amber / blue / green coding as the lecture diagrams. The right
column is the validated, typed output.

Palette: Slate & Stone (cool neutrals, slate-blue primary — no purple).
"""

from __future__ import annotations

import html
import json

import gradio as gr

from inspect_run import tool_definitions
from schemas import NeedMoreInfo, TravelBriefing
from trace import run

# ---- Dark palette (black bg, white text) ------------------------------------
BG = "#0D1017"        # page background (reads as black)
CARD = "#161A22"      # cards / inputs / trace rows
TEXT = "#E8EAED"      # near-white body text
MUTED = "#9AA3AF"
PRIMARY = "#7AA2E3"   # light slate-blue, readable on dark
BORDER = "#2A2F3A"
ROW = {  # trace-row accents, brightened for a dark background
    "thought": "#E0A64B",       # ochre
    "action": "#6FA8FF",        # blue
    "observation": "#57C784",   # green
    "retry": "#E0A64B",
    "final": "#57C784",
}
ICON = {"thought": "💭", "action": "🔧", "observation": "📡", "retry": "↻", "final": "✅"}

# Force a real dark theme via Gradio theme tokens (robust across component internals).
DARK = gr.themes.Base(primary_hue="blue", neutral_hue="slate").set(
    body_background_fill=BG,
    body_text_color=TEXT,
    body_text_color_subdued=MUTED,
    background_fill_primary=CARD,
    background_fill_secondary=BG,
    block_background_fill=CARD,
    block_border_color=BORDER,
    block_label_text_color=TEXT,
    block_title_text_color=TEXT,
    input_background_fill=CARD,
    input_border_color=BORDER,
    input_placeholder_color=MUTED,
    border_color_primary=BORDER,
)

CSS = f"""
.gradio-container {{ background: {BG} !important; }}
.gradio-container, .gradio-container p, .gradio-container li, .gradio-container span,
.gradio-container h1, .gradio-container h2, .gradio-container h3, .gradio-container h4 {{
    color: {TEXT} !important;
}}
h3, h4 {{ color: {TEXT} !important; }}                 /* section headers, output card titles */
#title, #title h1 {{ color: {PRIMARY} !important; }}
.gradio-container textarea, .gradio-container input[type="text"] {{
    background: {CARD} !important; color: {TEXT} !important;
}}
.trace-row {{
    background: {CARD}; border: 1px solid {BORDER};
    border-left: 4px solid var(--accent); border-radius: 8px;
    padding: 10px 12px; margin: 8px 0;
}}
.trace-label {{ font-weight: 700; color: var(--accent) !important; font-size: 0.8rem;
    text-transform: uppercase; letter-spacing: 0.04em; }}
.trace-body {{ color: {TEXT} !important; white-space: pre-wrap;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.86rem; margin-top: 4px; }}
.card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; padding: 16px; }}
"""


def _row(kind: str, title: str, body: str) -> str:
    accent = ROW.get(kind, PRIMARY)
    return (
        f'<div class="trace-row" style="--accent:{accent}">'
        f'<div class="trace-label">{ICON.get(kind, "•")} {html.escape(title)}</div>'
        f'<div class="trace-body">{html.escape(body)}</div></div>'
    )


def _briefing_md(b: TravelBriefing) -> str:
    packing = "\n".join(f"- {item}" for item in b.packing) or "_(none)_"
    caveats = "\n".join(f"- {c}" for c in b.caveats)
    md = (
        f"### ✅ Travel Briefing — {b.destination}\n"
        f"**Weather** · {b.weather.temp_c} °C, {b.weather.condition}, wind {b.weather.wind_kph} kph  \n"
        f"**Currency** · {b.local_currency}  \n"
        f"**Budget** · {b.budget_note}\n\n"
        f"**Pack**\n{packing}\n"
    )
    if caveats:
        md += f"\n**Caveats**\n{caveats}\n"
    return md


def _needinfo_md(n: NeedMoreInfo) -> str:
    return f"### 🤔 Need more info\n**Question** · {n.question}\n\n**Why** · {n.reason}\n"


def _raw_json(raw_messages: list) -> str:
    """Tool-definition JSON (what the model receives) + the raw message log."""
    return json.dumps(
        {"tool_definitions": tool_definitions(), "messages": raw_messages},
        indent=2,
        default=str,
    )


def on_run(query: str):
    if not query.strip():
        return "<div class='card'>Type a query above.</div>", "", "{}"
    try:
        # trace.run() already degrades guardrail/retry-budget failures gracefully;
        # this except is a safety net for anything unexpected (auth, bugs).
        steps, output, seq, raw_messages = run(query)
    except Exception as e:
        return _row("retry", "Error", f"{type(e).__name__}: {e}"), "", "{}"

    trace_html = "".join(_row(s.kind, s.title, s.body) for s in steps)
    trace_html += (
        f"<div class='trace-row' style='--accent:{PRIMARY}'>"
        f"<div class='trace-label'>Σ Tool sequence</div>"
        f"<div class='trace-body'>{html.escape(' → '.join(seq) or '(no tools called)')}</div></div>"
    )

    if isinstance(output, TravelBriefing):
        out_md = _briefing_md(output)
    elif isinstance(output, NeedMoreInfo):
        out_md = _needinfo_md(output)
    else:
        out_md = f"```\n{output!r}\n```"
    return trace_html, out_md, _raw_json(raw_messages)


EXAMPLES = [
    "What should I pack for the capital of France, and is $100 a lot there?",
    "I'm deciding between Tokyo and Lisbon this week — pack for whichever is warmer.",
    "What should I pack for my trip?",
    "Pack for a trip to Zorbania and tell me the exchange rate.",
]


with gr.Blocks(title="Single-Agent Lab") as demo:
    gr.Markdown("# Travel Briefing Agent", elem_id="title")
    gr.Markdown(
        "An LLM + four tools + a loop. Watch it **reason**, **call a tool**, **observe**, "
        "and loop until it can answer — then return a *validated* typed result."
    )
    with gr.Row():
        query = gr.Textbox(label="Ask", placeholder="e.g. Pack for the capital of Japan…", scale=4)
        go = gr.Button("Run", variant="primary", scale=1)
    gr.Examples(EXAMPLES, inputs=query, label="Try one")
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("#### The loop (Thought → Action → Observation)")
            trace_out = gr.HTML()
        with gr.Column(scale=2):
            gr.Markdown("#### Validated output")
            output_out = gr.Markdown()

    with gr.Accordion("Raw JSON — tool schemas (sent to the model) + model messages", open=False):
        gr.Markdown(
            "Tool *descriptions* live in this JSON — auto-generated from each tool's "
            "signature + docstring — **not** in the system prompt. Below that: the "
            "model's actual `tool-call` / `tool-return` messages."
        )
        raw_out = gr.Code(language="json", label="run JSON")

    go.click(on_run, inputs=query, outputs=[trace_out, output_out, raw_out])
    query.submit(on_run, inputs=query, outputs=[trace_out, output_out, raw_out])


if __name__ == "__main__":
    # Gradio 6 takes theme/css on launch(); older versions accept them on Blocks.
    try:
        demo.launch(theme=DARK, css=CSS)
    except TypeError:
        demo.css = CSS
        demo.theme = DARK
        demo.launch()
