from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "tono"


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
    override = os.getenv("TONO_APPDATA")
    if override:
        return Path(override).expanduser().resolve()

    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            base_dir = Path.home() / "Library" / "Application Support"
        elif sys.platform == "linux":
            xdg = os.getenv("XDG_DATA_HOME")
            base_dir = Path(xdg) if xdg else Path.home() / ".local" / "share"
        else:
            local_appdata = os.getenv("LOCALAPPDATA")
            base_dir = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
        return (base_dir / APP_NAME).resolve()

    return project_root()


def demo_dir() -> Path:
    bundled = resource_root() / "demo"
    if bundled.exists():
        return bundled
    return project_root() / "demo"


def input_dir() -> Path:
    return app_data_dir() / "input"


def output_dir() -> Path:
    return app_data_dir() / "output"


def plugins_dir() -> Path:
    return app_data_dir() / "plugins"


def plugins_enabled(*, native: bool) -> bool:
    """
    Return True when the plugin system should be active.

    Default behaviour: enabled on native/desktop builds, disabled for web.
    Override with the TONO_PLUGINS environment variable:
      TONO_PLUGINS=1   – force on  (useful for testing plugins via main.py)
      TONO_PLUGINS=0   – force off (disable even on native builds)
    """
    env = os.getenv("TONO_PLUGINS", "").strip().lower()
    if env in ("1", "true", "yes"):
        return True
    if env in ("0", "false", "no"):
        return False
    return native


def ensure_runtime_dirs(*, with_plugins: bool = False) -> None:
    input_dir().mkdir(parents=True, exist_ok=True)
    output_dir().mkdir(parents=True, exist_ok=True)
    if with_plugins:
        plugins_dir().mkdir(parents=True, exist_ok=True)
