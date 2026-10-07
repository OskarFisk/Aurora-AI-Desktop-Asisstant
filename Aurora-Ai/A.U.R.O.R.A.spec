# PyInstaller one-file Windows desktop build. Only AURORA.exe is released.
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH)


def source_tree(folder: str) -> list[tuple[str, str]]:
    root = ROOT / folder
    entries = []
    for path in root.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        destination = (Path(folder) / path.relative_to(root).parent).as_posix()
        entries.append((str(path), destination))
    return entries


def dynamic_imports() -> set[str]:
    """Keep imports used by action/plugin modules loaded from source files."""
    names: set[str] = set()
    for folder in ("actions", "plugins"):
        for path in (ROOT / folder).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.add(node.module.split(".", 1)[0])
    available = set()
    for name in names:
        try:
            if importlib.util.find_spec(name) is not None:
                available.add(name)
        except (ImportError, ModuleNotFoundError, ValueError):
            continue
    return available


datas = []
for folder in ("actions", "plugins", "core", "memory", "config",
               "dashboard/static", "assets"):
    datas.extend(source_tree(folder))
datas.append((str(ROOT / "main.py"), "."))

hiddenimports = sorted(dynamic_imports())
for package in ("google.genai", "mediapipe", "openwakeword"):
    try:
        if importlib.util.find_spec(package) is not None:
            hiddenimports.extend(collect_submodules(package))
    except (ImportError, ModuleNotFoundError, ValueError):
        continue

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "IPython", "notebook", "torch", "tensorflow"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="A.U.R.O.R.A",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "aurora_icon.ico"),
)
