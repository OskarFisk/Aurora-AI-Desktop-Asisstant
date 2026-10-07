from __future__ import annotations

import ast
from pathlib import Path

from core import circuit_hud
from core.user_paths import get_user_data_dir
from diagnostics import collect_diagnostics
from memory.config_manager import DEFAULT_ASSISTANT_NAME, normalize_assistant_name
from plugins import circuit_assembler, daily_briefing


def test_brand_migrates_legacy_defaults_and_preserves_custom_names():
    assert DEFAULT_ASSISTANT_NAME == "A.U.R.O.R.A"
    assert normalize_assistant_name(None) == DEFAULT_ASSISTANT_NAME
    assert normalize_assistant_name("J.A.R.V.I.S") == DEFAULT_ASSISTANT_NAME
    assert normalize_assistant_name("Custom") == "Custom"


def test_ten_theme_presets_are_distinct_hex_colors():
    root = Path(__file__).resolve().parents[1]
    ui_tree = ast.parse((root / "ui.py").read_text(encoding="utf-8"))
    assignment = next(
        node for node in ui_tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "THEME_PRESETS"
                for target in node.targets)
    )
    theme_presets = ast.literal_eval(assignment.value)

    assert len(theme_presets) == 10
    colors = [color for _, color in theme_presets]
    assert len(set(colors)) == 10
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


def test_diagnostics_report_missing_runtime_requirements_without_reading_config(tmp_path):
    diagnostics = collect_diagnostics(
        root=tmp_path,
        python_version=(3, 12),
        system="Windows",
        module_finder=lambda _name: False,
        command_finder=lambda _name: None,
    )

    assert any(item.status == "FAIL" and item.name == "Python version" for item in collect_diagnostics(
        root=tmp_path,
        python_version=(3, 10),
        system="Windows",
        module_finder=lambda _name: True,
    ))
    assert sum(item.status == "FAIL" for item in diagnostics) >= 5
    assert not (tmp_path / "config" / "api_keys.json").exists()


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
