"""Generate a self-contained, browser-rendered circuit hologram."""
from __future__ import annotations

import html
import json
import webbrowser
from pathlib import Path

from core.user_paths import get_user_data_dir

OUTPUT_DIR = get_user_data_dir() / "circuits"


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def generate_circuit_html(data: dict) -> str:
    """Render circuit cards, safety notes, wire mapping, and firmware offline."""
    title = _e(data.get("title", "Circuit schematic"))
    description = _e(data.get("description", ""))
    components = data.get("components", [])
    wires = data.get("wires", [])
    warnings = data.get("warnings", [])
    steps = data.get("steps", [])
    code = _e(data.get("arduino_code", ""))

    cards = "".join(
        '<article class="card"><h2>'
        + _e(component.get("name", "Component"))
        + '</h2><p>'
        + _e(component.get("subtitle", ""))
        + '</p><div class="pins">'
        + " · ".join(
            _e(pin.get("name", ""))
            for side in ("left_pins", "right_pins")
            for pin in component.get(side, [])
        )
        + "</div></article>"
        for component in components
    )
    wire_rows = "".join(
        '<li><i style="--wire:'
        + _e(wire.get("color", "#57e8ff"))
        + '"></i><b>'
        + _e(wire.get("label", "Connection"))
        + '</b><span>'
        + _e(wire.get("from", "?"))
        + " → "
        + _e(wire.get("to", "?"))
        + "</span></li>"
        for wire in wires
    )
    warning_rows = "".join(f"<li>{_e(warning)}</li>" for warning in warnings)
    step_rows = "".join(f"<li>{_e(step)}</li>" for step in steps)
    safe_json = json.dumps(
        {"wires": wires, "components": components},
        ensure_ascii=True,
    ).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title} // A.U.R.O.R.A</title>
<style>
:root{{--bg:#050812;--panel:#0b1221;--line:#183348;--cyan:#57e8ff;--violet:#ae8aff;--text:#e1f6ff;--muted:#82a7b6}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(ellipse at 50% -20%,#17314c,#050812 65%);color:var(--text);font:15px/1.6 Segoe UI,Arial,sans-serif;padding:32px}}
main{{max-width:1080px;margin:auto}}.eyebrow{{color:var(--cyan);letter-spacing:.24em;font:12px Consolas,monospace}}h1{{font-size:clamp(27px,5vw,48px);line-height:1.1;margin:.35em 0}}.desc{{color:var(--muted);max-width:72ch}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:25px 0}}.card,.panel{{background:linear-gradient(145deg,#101d2cdd,#09111ddd);border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 8px 32px #0005}}.card h2{{margin:0;color:var(--cyan);font-size:19px}}.card p{{color:var(--muted)}}.pins{{color:#d2c1ff;font:13px Consolas,monospace}}
.columns{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}}h3{{color:var(--violet);font:13px Consolas,monospace;letter-spacing:.12em}}ul,ol{{padding-left:20px}}li{{padding:5px 0}}.wire-list li{{display:grid;grid-template-columns:12px minmax(110px,.7fr) 1fr;gap:10px;align-items:center}}.wire-list i{{width:10px;height:10px;border-radius:50%;background:var(--wire);box-shadow:0 0 12px var(--wire)}}.wire-list span{{font:12px Consolas,monospace;color:var(--muted);overflow-wrap:anywhere}}
.warning{{border-color:#795020;background:linear-gradient(145deg,#30200d,#0b1221)}}.warning h3{{color:#ffc66d}}.code{{white-space:pre-wrap;overflow-wrap:anywhere;background:#040910;padding:16px;border-radius:9px;color:#b4f2ff}}
@media(max-width:600px){{body{{padding:18px}}}}
</style><main><div class="eyebrow">A.U.R.O.R.A // CIRCUIT HOLOGRAM</div><h1>{title}</h1><p class="desc">{description}</p>
<section class="grid">{cards}</section><section class="columns"><article class="panel"><h3>◈ CONNECTION MAP</h3><ul class="wire-list">{wire_rows}</ul></article>
<article class="panel"><h3>◈ BUILD SEQUENCE</h3><ol>{step_rows}</ol></article></section>
<section class="panel warning"><h3>⚠ ELECTRICAL SAFETY</h3><ul>{warning_rows}</ul></section>
<section class="panel"><h3>◈ FIRMWARE</h3><pre class="code">{code}</pre></section>
<script type="application/json" id="circuit-data">{safe_json}</script></main></html>"""


def show_circuit_schematic(data: dict) -> Path:
    """Write the local schematic and open it in the system browser."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / "circuit_schematic.html"
    target.write_text(generate_circuit_html(data), encoding="utf-8")
    webbrowser.open(target.resolve().as_uri())
    return target
