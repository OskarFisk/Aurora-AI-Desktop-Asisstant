from __future__ import annotations

import ast
from pathlib import Path

from core import circuit_hud
from core.user_paths import get_user_data_dir
from memory.config_manager import DEFAULT_ASSISTANT_NAME, normalize_assistant_name
from plugins import circuit_assembler, daily_briefing
from ui import THEME_PRESETS


def test_brand_migrates_legacy_defaults_and_preserves_custom_names():
    assert DEFAULT_ASSISTANT_NAME == "A.U.R.O.R.A"
    assert normalize_assistant_name(None) == DEFAULT_ASSISTANT_NAME
    assert normalize_assistant_name("J.A.R.V.I.S") == DEFAULT_ASSISTANT_NAME
    assert normalize_assistant_name("Custom") == "Custom"


def test_six_theme_presets_are_distinct_hex_colors():
    assert len(THEME_PRESETS) == 6
    colors = [color for _, color in THEME_PRESETS]
    assert len(set(colors)) == 6
    assert all(len(color) == 7 and color.startswith("#") for color in colors)


def test_circuit_hud_escapes_user_supplied_html():
    document = circuit_hud.generate_circuit_html({
        "title": "<script>alert(1)</script>",
        "components": [{"name": "<img src=x>", "left_pins": [], "right_pins": []}],
        "wires": [{"label": "signal", "from": "A", "to": "B",
                   "color": '"><script>alert(1)</script>'}],
        "steps": ["Connect safely"],
        "warnings": ["Verify voltage"],
        "arduino_code": "void setup() {}",
    })
    assert "<script>alert(1)</script>" not in document
    assert "&lt;script&gt;" in document
    assert "&lt;img" in document


def test_frozen_resource_requirements_are_bundled():
    root = Path(__file__).resolve().parents[1]
    spec = ast.parse((root / "A.U.R.O.R.A.spec").read_text(encoding="utf-8"))
    folders = {
        node.value
        for node in ast.walk(spec)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value in {
            "actions", "plugins", "core", "memory", "config",
            "dashboard/static", "assets",
        }
    }
    assert {"actions", "plugins", "core", "dashboard/static", "assets"} <= folders
    assert (root / "core" / "prompt.txt").is_file()
    assert (root / "core" / "face_model.obj").is_file()
    assert (root / "assets" / "aurora_icon.png").is_file()
    assert (root / "assets" / "aurora_icon.ico").is_file()
    spec_text = (root / "A.U.R.O.R.A.spec").read_text(encoding="utf-8")
    assert 'icon=str(ROOT / "assets" / "aurora_icon.ico")' in spec_text


def test_user_data_folder_has_application_identity():
    assert get_user_data_dir().name == "Aurora-AI"


def test_daily_briefing_does_not_invent_weather_without_a_city():
    weather = daily_briefing._get_weather_intel()
    assert weather["status"] == "unavailable"
    assert "temp_c" not in weather


def test_unknown_circuit_does_not_show_an_unrelated_preset(monkeypatch):
    monkeypatch.setattr(circuit_assembler, "solve_circuit_with_ai", lambda **kwargs: None)
    result = circuit_assembler.circuit_assembler(
        action="assemble_components",
        components="unrecognized custom board",
        query="connect it to a compatible sensor",
    )
    assert result["status"] == "unavailable"
    assert "reliable schematic" in result["summary"]
