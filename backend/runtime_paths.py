from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Argonode"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return project_root()


def frontend_dir() -> Path:
    bundled = resource_root() / "frontend"
    if bundled.exists():
        return bundled
    return project_root() / "frontend"


def frontend_dist_dir() -> Path:
    return frontend_dir() / "dist"


def app_data_dir() -> Path:
    override = os.getenv("ARGONODE_APPDATA")
    if override:
        return Path(override).expanduser().resolve()

    if getattr(sys, "frozen", False):
        local_appdata = os.getenv("LOCALAPPDATA")
        base_dir = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
        return (base_dir / APP_NAME).resolve()

    return project_root()


def input_dir() -> Path:
    return app_data_dir() / "input"


def output_dir() -> Path:
    return app_data_dir() / "output"


def ensure_runtime_dirs() -> None:
    input_dir().mkdir(parents=True, exist_ok=True)
    output_dir().mkdir(parents=True, exist_ok=True)
