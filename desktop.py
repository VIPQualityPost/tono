from __future__ import annotations

import asyncio
import logging
import socket
import threading
import time
import urllib.request
from pathlib import Path

import webview
from aiohttp import web

from backend.runtime_paths import app_data_dir, ensure_runtime_dirs
from backend.server import create_app

HOST = "127.0.0.1"
WINDOW_TITLE = "tono"


class _Api:
    """Exposed to JavaScript as window.pywebview.api."""

    def __init__(self, window_ref: list):
        self._window_ref = window_ref

    def open_file_dialog(self) -> str | None:
        """Open a native file picker and return the selected path (or None)."""
        win = self._window_ref[0]
        if win is None:
            return None
        result = win.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=(
                "All supported (*.png;*.jpg;*.jpeg;*.tiff;*.tif;*.npy;*.npz;*.gwy;*.sxm;*.ibw)",
                "Images (*.png;*.jpg;*.jpeg;*.tiff;*.tif)",
                "NumPy (*.npy;*.npz)",
                "SPM (*.gwy;*.sxm;*.ibw)",
                "All files (*.*)",
            ),
        )
        if result and len(result) > 0:
            return result[0]
        return None

    def open_folder_dialog(self) -> str | None:
        """Open a native folder picker and return the selected path (or None)."""
        win = self._window_ref[0]
        if win is None:
            return None
        result = win.create_file_dialog(
            webview.FOLDER_DIALOG,
            allow_multiple=False,
        )
        if result and len(result) > 0:
            return result[0]
        return None

    def choose_save_workflow_png_path(self, default_filename: str = "workflow.png") -> str | None:
        """Open a native save dialog and return the chosen PNG path (or None)."""
        win = self._window_ref[0]
        if win is None:
            return None

        result = win.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=default_filename,
            file_types=(
                "PNG image (*.png)",
                "All files (*.*)",
            ),
        )
        if not result:
            return None

        path = Path(result[0] if isinstance(result, (list, tuple)) else result).expanduser()
        if path.suffix.lower() != ".png":
            path = path.with_suffix(".png")
        return str(path)


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def _wait_for_server(url: str, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5):
                return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for server at {url}")


def _run_server(host: str, port: int, ready: threading.Event, state: dict[str, object]) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    state["loop"] = loop

    async def start() -> None:
        app = create_app(loop, allow_local_filesystem=True)
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        state["runner"] = runner
        ready.set()

    try:
        loop.run_until_complete(start())
        loop.run_forever()
    except Exception as exc:
        state["error"] = exc
        ready.set()
        raise
    finally:
        runner = state.get("runner")
        if isinstance(runner, web.AppRunner):
            loop.run_until_complete(runner.cleanup())
        loop.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s - %(message)s",
    )

    ensure_runtime_dirs()

    port = _pick_free_port()
    base_url = f"http://{HOST}:{port}"
    ready = threading.Event()
    state: dict[str, object] = {}

    server_thread = threading.Thread(
        target=_run_server,
        args=(HOST, port, ready, state),
        name="tono-server",
        daemon=True,
    )
    server_thread.start()
    ready.wait(timeout=15.0)

    if "error" in state:
        raise RuntimeError("tono server failed to start") from state["error"]

    _wait_for_server(f"{base_url}/nodes")

    window_ref: list[webview.Window | None] = [None]
    js_api = _Api(window_ref)

    window = webview.create_window(
        WINDOW_TITLE,
        base_url,
        width=1600,
        height=1000,
        min_size=(1100, 720),
        js_api=js_api,
    )
    window_ref[0] = window

    def _shutdown() -> None:
        loop = state.get("loop")
        if isinstance(loop, asyncio.AbstractEventLoop):
            loop.call_soon_threadsafe(loop.stop)

    window.events.closed += _shutdown
    logging.getLogger(__name__).info("Using app data directory: %s", app_data_dir())
    webview.start()


if __name__ == "__main__":
    main()
