"""
aiohttp web server for argonode.

Routes
------
GET  /                  → serve frontend/index.html
GET  /static/{path}     → serve frontend JS/CSS
GET  /nodes             → JSON dict of all registered node definitions
POST /upload            → multipart file upload to input/
POST /prompt            → submit a workflow; returns {prompt_id}
GET  /ws                → WebSocket upgrade

WebSocket message types sent to clients
----------------------------------------
{"type": "execution_start",    "data": {"prompt_id": "..."}}
{"type": "executing",          "data": {"node": "...", "prompt_id": "..."}}
{"type": "preview",            "data": {"node_id": "...", "image": "data:..."}}
{"type": "table",              "data": {"node_id": "...", "rows": [...]}}
{"type": "execution_error",    "data": {"node_id": "...", "message": "..."}}
{"type": "execution_complete", "data": {"prompt_id": "..."}}
"""

from __future__ import annotations
import asyncio
import json
import logging
import uuid
from pathlib import Path

from aiohttp import web, WSMsgType

log = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
DIST_DIR     = FRONTEND_DIR / "dist"
INPUT_DIR    = Path(__file__).parent.parent / "input"
OUTPUT_DIR   = Path(__file__).parent.parent / "output"


# ---------------------------------------------------------------------------
# JSON helper — numpy scalars are not serialisable by default
# ---------------------------------------------------------------------------

class _SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def _dumps(obj) -> str:
    return json.dumps(obj, cls=_SafeEncoder)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(loop: asyncio.AbstractEventLoop) -> web.Application:
    # Import nodes to trigger registration decorators
    import backend.nodes  # noqa: F401
    from backend.node_registry import get_all_node_info
    from backend.execution import ExecutionEngine, new_prompt_id

    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    engine = ExecutionEngine()
    websockets: set[web.WebSocketResponse] = set()

    # ------------------------------------------------------------------
    # WebSocket broadcast helpers
    # ------------------------------------------------------------------

    def broadcast(msg: dict) -> None:
        """Schedule a broadcast to all connected WebSocket clients."""
        payload = _dumps(msg)
        for ws in list(websockets):
            if not ws.closed:
                asyncio.run_coroutine_threadsafe(ws.send_str(payload), loop)

    def on_preview(node_id: str, data_uri: str) -> None:
        broadcast({"type": "preview", "data": {"node_id": node_id, "image": data_uri}})

    def on_table(node_id: str, rows: list) -> None:
        broadcast({"type": "table", "data": {"node_id": node_id, "rows": rows}})

    def on_mesh(node_id: str, mesh_data: dict) -> None:
        broadcast({"type": "mesh3d", "data": {"node_id": node_id, "mesh": mesh_data}})

    def on_overlay(node_id: str, overlay_data) -> None:
        broadcast({"type": "overlay", "data": {"node_id": node_id, "overlay": overlay_data}})

    # ------------------------------------------------------------------
    # Route handlers
    # ------------------------------------------------------------------

    async def index(request: web.Request) -> web.Response:
        # Serve Vite build output if available, else raw frontend
        if (DIST_DIR / "index.html").exists():
            return web.FileResponse(DIST_DIR / "index.html")
        return web.FileResponse(FRONTEND_DIR / "index.html")

    async def get_nodes(request: web.Request) -> web.Response:
        info = get_all_node_info()
        return web.Response(
            text=_dumps(info),
            content_type="application/json",
        )

    async def list_files(request: web.Request) -> web.Response:
        """List files in the input/ directory for the file picker widget."""
        files = sorted(
            f.name for f in INPUT_DIR.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ) if INPUT_DIR.exists() else []
        return web.Response(text=_dumps(files), content_type="application/json")

    async def browse_dir(request: web.Request) -> web.Response:
        """
        Server-side directory browser for local file picking.
        GET /browse?dir=/some/path → {parent, dirs[], files[]}
        """
        dir_path = request.query.get("dir", str(Path.home()))
        p = Path(dir_path).expanduser().resolve()

        if not p.is_dir():
            raise web.HTTPBadRequest(reason=f"Not a directory: {p}")

        dirs = []
        files = []
        try:
            for entry in sorted(p.iterdir(), key=lambda e: e.name.lower()):
                if entry.name.startswith("."):
                    continue
                if entry.is_dir():
                    dirs.append(entry.name)
                elif entry.is_file():
                    files.append(entry.name)
        except PermissionError:
            pass

        return web.Response(
            text=_dumps({
                "path": str(p),
                "parent": str(p.parent) if p.parent != p else None,
                "dirs": dirs,
                "files": files,
            }),
            content_type="application/json",
        )

    async def upload_file(request: web.Request) -> web.Response:
        reader = await request.multipart()
        field = await reader.next()
        if field is None or field.name != "file":
            raise web.HTTPBadRequest(reason="Expected a 'file' field in multipart body")

        filename = Path(field.filename).name  # strip any path traversal
        dest = INPUT_DIR / filename
        with open(dest, "wb") as f:
            while True:
                chunk = await field.read_chunk(65536)
                if not chunk:
                    break
                f.write(chunk)

        return web.Response(text=_dumps({"filename": filename}), content_type="application/json")

    async def submit_prompt(request: web.Request) -> web.Response:
        body = await request.json()
        prompt = body.get("prompt")
        if not isinstance(prompt, dict) or not prompt:
            raise web.HTTPBadRequest(reason="'prompt' must be a non-empty dict")

        prompt_id = new_prompt_id()

        # Run execution in a thread pool so scipy doesn't block the event loop
        async def run():
            broadcast({"type": "execution_start", "data": {"prompt_id": prompt_id}})

            def on_start(node_id: str) -> None:
                broadcast({"type": "executing", "data": {"node": node_id, "prompt_id": prompt_id}})

            try:
                await loop.run_in_executor(
                    None,
                    lambda: engine.execute(
                        prompt,
                        on_node_start=on_start,
                        on_preview=on_preview,
                        on_table=on_table,
                        on_mesh=on_mesh,
                        on_overlay=on_overlay,
                    ),
                )
                broadcast({"type": "execution_complete", "data": {"prompt_id": prompt_id}})
            except Exception as exc:
                log.exception("Execution error")
                broadcast({
                    "type": "execution_error",
                    "data": {"node_id": "", "message": str(exc)},
                })

        asyncio.ensure_future(run())
        return web.Response(
            text=_dumps({"prompt_id": prompt_id}),
            content_type="application/json",
        )

    async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        websockets.add(ws)
        log.info("WebSocket client connected (%d total)", len(websockets))
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    pass  # clients don't need to send anything currently
                elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
        finally:
            websockets.discard(ws)
            log.info("WebSocket client disconnected (%d total)", len(websockets))
        return ws

    # ------------------------------------------------------------------
    # App assembly
    # ------------------------------------------------------------------

    app = web.Application()

    app.router.add_get("/", index)
    app.router.add_get("/nodes", get_nodes)
    app.router.add_get("/files", list_files)
    app.router.add_get("/browse", browse_dir)
    app.router.add_post("/upload", upload_file)
    app.router.add_post("/prompt", submit_prompt)
    app.router.add_get("/ws", websocket_handler)

    # Serve frontend static files (Vite build or raw)
    if DIST_DIR.exists():
        app.router.add_static("/assets", DIST_DIR / "assets")
    app.router.add_static("/static", FRONTEND_DIR)

    # CORS — allow any origin (local dev only)
    async def _cors_middleware(app_, handler):
        async def middleware(request):
            if request.method == "OPTIONS":
                return web.Response(headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                })
            response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
        return middleware

    app.middlewares.append(_cors_middleware)

    return app
