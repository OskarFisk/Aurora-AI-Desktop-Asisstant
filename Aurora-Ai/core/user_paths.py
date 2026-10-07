"""Per-user writable data paths shared by bundled and source-run features."""
from __future__ import annotations

import os
import platform
from pathlib import Path

APP_DATA_DIR = "Aurora-AI"


def get_user_data_dir() -> Path:
    """Return and create the platform's standard per-user A.U.R.O.R.A folder."""
    if platform.system() == "Windows":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
    elif platform.system() == "Darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    data_dir = root / APP_DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
