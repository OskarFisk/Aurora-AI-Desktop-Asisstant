"""Read-only startup diagnostics for A.U.R.O.R.A source installs."""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

APP_DIR = Path(__file__).resolve().parent

_REQUIRED_MODULES = {
    "PyQt6 desktop UI": "PyQt6",
    "Gemini client": "google.genai",
    "Numerical runtime": "numpy",
    "Audio device interface": "sounddevice",
    "System monitoring": "psutil",
}
_REQUIRED_FILES = (
    "core/prompt.txt",
    "core/face_model.obj",
    "assets/aurora_icon.png",
    "assets/aurora_icon.ico",
)
_OPTIONAL_LINUX_TOOLS = {
    "Open URLs": "xdg-open",
    "Volume controls": "pactl",
    "Brightness controls": "brightnessctl",
}


@dataclass(frozen=True)
class Diagnostic:
    status: str
    name: str
    details: str


def _module_exists(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def collect_diagnostics(
    root: Path = APP_DIR,
    python_version: tuple[int, int] | None = None,
    system: str | None = None,
    module_finder: Callable[[str], object] | None = None,
    command_finder: Callable[[str], str | None] | None = None,
) -> list[Diagnostic]:
    """Collect local readiness checks without changing files or reading secrets."""
    version = python_version or sys.version_info[:2]
    current_system = system or platform.system()
    module_finder = module_finder or _module_exists
    command_finder = command_finder or shutil.which
    results: list[Diagnostic] = []

    if version < (3, 12):
        results.append(Diagnostic("FAIL", "Python version", "Python 3.12 or newer is required."))
    elif version > (3, 13):
        results.append(Diagnostic("WARN", "Python version", "Newer than the tested Python 3.13 ceiling."))
    else:
        results.append(Diagnostic("OK", "Python version", f"Python {version[0]}.{version[1]} is supported."))

    for label, module_name in _REQUIRED_MODULES.items():
        if module_finder(module_name):
            results.append(Diagnostic("OK", label, f"{module_name} is installed."))
        else:
            results.append(Diagnostic("FAIL", label, f"Missing {module_name}; install requirements.txt."))

    for relative_path in _REQUIRED_FILES:
        if (root / relative_path).is_file():
            results.append(Diagnostic("OK", f"Resource: {relative_path}", "Present."))
        else:
            results.append(Diagnostic("FAIL", f"Resource: {relative_path}", "Missing from this checkout."))

    if current_system == "Linux":
        for label, command in _OPTIONAL_LINUX_TOOLS.items():
            if command_finder(command):
                results.append(Diagnostic("OK", label, f"{command} is available."))
            else:
                results.append(Diagnostic("WARN", label, f"Optional {command} command is not installed."))

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check A.U.R.O.R.A local runtime readiness.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args(argv)
    results = collect_diagnostics()

    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        for result in results:
            print(f"[{result.status}] {result.name}: {result.details}")
        failures = sum(result.status == "FAIL" for result in results)
        warnings = sum(result.status == "WARN" for result in results)
        print(f"\n{failures} failure(s), {warnings} warning(s).")

    return 1 if any(result.status == "FAIL" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())