"""Gradio UI — the trace panel is the whole point.

The left column is the ReAct loop made visible: Thought / Action / Observation
rows in the same amber / blue / green coding as the lecture diagrams. The right
column is the validated, typed output.

Palette: Slate & Stone (cool neutrals, slate-blue primary — no purple).
"""

from __future__ import annotations

import html

import gradio as gr

from schemas import NeedMoreInfo, TravelBriefing
from trace import run

try:
    from pydantic_ai import UsageLimitExceeded
except Exception:  # pragma: no cover - import path varies by version
    from pydantic_ai.usage import UsageLimitExceeded  # type: ignore

# ---- Slate & Stone palette --------------------------------------------------
BG = "#F5F6F7"
TEXT = "#222831"
PRIMARY = "#3D5A80"
CARD = "#FFFFFF"
BORDER = "#DCE0E4"
ROW = {  # trace-row accent colors, carried over from the lecture diagrams
    "thought": "#B7791F",       # ochre
    "action": "#2B6CB0",        # blue
    "observation": "#2F855A",   # green
    "retry": "#B7791F",
    "final": "#276749",         # deep green
}
ICON = {"thought": "💭", "action": "🔧", "observation": "📡", "retry": "↻", "final": "✅"}

CSS = f"""
.gradio-container {{ background: {BG}; color: {TEXT}; }}
#title {{ color: {PRIMARY}; }}
.trace-row {{
    background: {CARD}; border: 1px solid {BORDER};
    border-left: 4px solid var(--accent); border-radius: 8px;
    padding: 10px 12px; margin: 8px 0;
}}
.trace-label {{ font-weight: 700; color: var(--accent); font-size: 0.8rem;
    text-transform: uppercase; letter-spacing: 0.04em; }}
.trace-body {{ color: {TEXT}; white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.86rem; margin-top: 4px; }}
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


def on_run(query: str):
    if not query.strip():
        return "<div class='card'>Type a query above.</div>", ""
    try:
        trace, output, seq = run(query)
    except UsageLimitExceeded as e:
        return _row("retry", "Guardrail hit", str(e)), "### 🛑 Stopped\nThe run exceeded its `UsageLimits`."
    except Exception as e:  # surface tool/network/auth errors plainly for a demo
        return _row("retry", "Error", f"{type(e).__name__}: {e}"), ""

    trace_html = "".join(_row(s.kind, s.title, s.body) for s in trace)
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
    return trace_html, out_md


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

    go.click(on_run, inputs=query, outputs=[trace_out, output_out])
    query.submit(on_run, inputs=query, outputs=[trace_out, output_out])


if __name__ == "__main__":
    # Gradio 6 takes theme/css on launch(); older versions accept them on Blocks.
    try:
        demo.launch(theme=gr.themes.Base(), css=CSS)
    except TypeError:
        demo.css = CSS
        demo.theme = gr.themes.Base()
        demo.launch()
