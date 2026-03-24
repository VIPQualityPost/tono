from __future__ import annotations

import asyncio
import logging
import socket
import threading
import time
import urllib.request

import webview
from aiohttp import web

from backend.runtime_paths import app_data_dir, ensure_runtime_dirs
from backend.server import create_app

HOST = "127.0.0.1"
WINDOW_TITLE = "Argonode"


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
        app = create_app(loop)
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
        name="argonode-server",
        daemon=True,
    )
    server_thread.start()
    ready.wait(timeout=15.0)

    if "error" in state:
        raise RuntimeError("Argonode server failed to start") from state["error"]

    _wait_for_server(f"{base_url}/nodes")

    window = webview.create_window(
        WINDOW_TITLE,
        base_url,
        width=1600,
        height=1000,
        min_size=(1100, 720),
    )

    def _shutdown() -> None:
        loop = state.get("loop")
        if isinstance(loop, asyncio.AbstractEventLoop):
            loop.call_soon_threadsafe(loop.stop)

    window.events.closed += _shutdown
    logging.getLogger(__name__).info("Using app data directory: %s", app_data_dir())
    webview.start()


if __name__ == "__main__":
    main()
