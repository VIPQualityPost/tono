"""
aiohttp web server for argonode.

Routes
------
GET  /                  → serve frontend/index.html
GET  /static/{path}     → serve frontend JS/CSS
GET  /nodes             → JSON dict of all registered node definitions
GET  /files             → list files in the current session upload workspace
GET  /folder-files      → list compatible files in a picked folder
GET  /channels          → inspect channels for a picked file
POST /upload            → multipart file upload to the current session workspace
POST /upload-folder     → create a folder in the current session workspace
POST /prompt            → submit a workflow; returns {prompt_id}
GET  /ws                → WebSocket upgrade

WebSocket message types sent to clients
----------------------------------------
{"type": "execution_start",    "data": {"prompt_id": "..."}}
{"type": "executing",          "data": {"node": "...", "prompt_id": "..."}}
{"type": "preview",            "data": {"node_id": "...", "image": "data:..."}}
{"type": "table",              "data": {"node_id": "...", "rows": [...]} }
{"type": "scalar",             "data": {"node_id": "...", "value": 1.23, "unit": "nm"}}
{"type": "node_timing",        "data": {"node_id": "...", "elapsed_ms": 12.34}}
{"type": "execution_error",    "data": {"node_id": "...", "message": "..."}}
{"type": "execution_complete", "data": {"prompt_id": "..."}}
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from aiohttp import web, WSMsgType

from backend.frontend_build import FrontendBuildError, ensure_frontend_dist_ready
from backend.runtime_paths import ensure_runtime_dirs, frontend_dir, frontend_dist_dir, plugins_dir, plugins_enabled, project_root
from backend.session_runtime import (
    PATH_INPUT_TYPES,
    SESSION_HEADER,
    SESSION_QUERY,
    ensure_session_runtime_dirs,
    normalize_relative_upload_path,
    resolve_client_path,
    server_path_to_client_path,
    session_input_dir,
    session_upload_uri,
    validate_session_id,
)

log = logging.getLogger(__name__)

FRONTEND_DIR = frontend_dir()
DIST_DIR = frontend_dist_dir()
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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


def _sanitize_non_finite(obj):
    """Recursively replace non-finite floats so they survive JSON serialization."""
    if isinstance(obj, float):
        if math.isnan(obj):
            return "NaN"
        if math.isinf(obj):
            return "∞" if obj > 0 else "-∞"
    elif isinstance(obj, dict):
        return {k: _sanitize_non_finite(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_non_finite(v) for v in obj]
    return obj


def _dumps(obj) -> str:
    return json.dumps(obj, cls=_SafeEncoder)


def save_png_bytes(target_path: str, payload: bytes) -> Path:
    path = Path(target_path).expanduser()
    if not target_path.strip():
        raise ValueError("Missing save path")
    if path.suffix.lower() != ".png":
        path = path.with_suffix(".png")
    if not payload.startswith(PNG_SIGNATURE):
        raise ValueError("Payload is not a valid PNG")
    path.write_bytes(payload)
    return path


def create_app(
    loop: asyncio.AbstractEventLoop,
    *,
    allow_local_filesystem: bool = False,
) -> web.Application:
    import backend.nodes  # noqa: F401

    _plugins_on = plugins_enabled(native=allow_local_filesystem)
    if _plugins_on:
        from backend.plugin_loader import load_plugins
        load_plugins(plugins_dir())

    from backend.execution import ExecutionEngine, new_prompt_id
    from backend.node_registry import NODE_CLASS_MAPPINGS, get_all_node_info

    ensure_runtime_dirs(with_plugins=_plugins_on)

    session_engines: dict[str, ExecutionEngine] = {}
    session_websockets: dict[str, set[web.WebSocketResponse]] = defaultdict(set)

    def _is_link(value) -> bool:
        return (
            isinstance(value, (list, tuple))
            and len(value) == 2
            and isinstance(value[0], str)
            and isinstance(value[1], int)
        )

    def require_session_id(request: web.Request) -> str:
        raw_session = request.headers.get(SESSION_HEADER) or request.query.get(SESSION_QUERY)
        if not raw_session:
            if allow_local_filesystem:
                raw_session = "desktop-local-session"
            else:
                raise web.HTTPBadRequest(reason="Missing session id")

        try:
            session_id = validate_session_id(raw_session)
        except ValueError as exc:
            raise web.HTTPBadRequest(reason=str(exc)) from exc

        ensure_session_runtime_dirs(session_id)
        return session_id

    def get_session_engine(session_id: str) -> ExecutionEngine:
        engine = session_engines.get(session_id)
        if engine is None:
            engine = ExecutionEngine()
            session_engines[session_id] = engine
        return engine

    def resolve_request_path(session_id: str, raw_value: str) -> Path:
        try:
            return resolve_client_path(
                raw_value,
                session_id=session_id,
                allow_local_filesystem=allow_local_filesystem,
            )
        except PermissionError as exc:
            raise web.HTTPForbidden(reason=str(exc)) from exc
        except ValueError as exc:
            raise web.HTTPBadRequest(reason=str(exc)) from exc

    def rewrite_prompt_paths(prompt: dict, session_id: str) -> dict:
        normalized = deepcopy(prompt)
        for node_def in normalized.values():
            class_name = node_def.get("class_type")
            cls = NODE_CLASS_MAPPINGS.get(class_name)
            if cls is None:
                continue

            input_types = cls.INPUT_TYPES()
            specs = {}
            specs.update(input_types.get("required", {}))
            specs.update(input_types.get("optional", {}))

            inputs = node_def.get("inputs", {})
            if not isinstance(inputs, dict):
                continue

            for input_name, raw_value in list(inputs.items()):
                if _is_link(raw_value) or not isinstance(raw_value, str):
                    continue
                if not raw_value.strip():
                    continue

                spec = specs.get(input_name)
                input_type = spec[0] if isinstance(spec, (list, tuple)) and spec else spec
                if not isinstance(input_type, str):
                    continue
                if input_type not in PATH_INPUT_TYPES:
                    continue

                inputs[input_name] = str(resolve_request_path(session_id, raw_value))
        return normalized

    def broadcast(session_id: str, msg: dict) -> None:
        payload = _dumps(msg)
        for ws in list(session_websockets.get(session_id, ())):
            if not ws.closed:
                asyncio.run_coroutine_threadsafe(ws.send_str(payload), loop)

    def on_preview(session_id: str, node_id: str, data_uri: str) -> None:
        broadcast(session_id, {"type": "preview", "data": {"node_id": node_id, "image": data_uri}})

    def on_table(session_id: str, node_id: str, rows: list) -> None:
        broadcast(session_id, {"type": "table", "data": {"node_id": node_id, "rows": _sanitize_non_finite(rows)}})

    def on_mesh(session_id: str, node_id: str, mesh_data: dict) -> None:
        broadcast(session_id, {"type": "mesh3d", "data": {"node_id": node_id, "mesh": mesh_data}})

    def on_overlay(session_id: str, node_id: str, overlay_data) -> None:
        broadcast(session_id, {"type": "overlay", "data": {"node_id": node_id, "overlay": overlay_data}})

    def on_value(session_id: str, node_id: str, payload) -> None:
        if isinstance(payload, dict):
            value = payload.get("value")
            unit = payload.get("unit", "")
        else:
            value = payload
            unit = ""

        # JSON cannot encode non-finite floats; convert to string representations.
        if isinstance(value, float) and not math.isfinite(value):
            value = "∞" if value > 0 else ("-∞" if math.isinf(value) else "NaN")

        data = {"node_id": node_id, "value": value}
        if isinstance(unit, str) and unit.strip():
            data["unit"] = unit.strip()
        broadcast(session_id, {"type": "scalar", "data": data})

    def on_warning(session_id: str, node_id: str, message: str) -> None:
        broadcast(session_id, {"type": "node_warning", "data": {"node_id": node_id, "message": message}})

    async def index(request: web.Request) -> web.Response:
        if not getattr(sys, "frozen", False):
            try:
                await loop.run_in_executor(
                    None,
                    lambda: ensure_frontend_dist_ready(
                        project_root(),
                        FRONTEND_DIR,
                        DIST_DIR,
                        logger=log,
                    ),
                )
            except FrontendBuildError as exc:
                log.error("Unable to refresh frontend build: %s", exc)
                return web.Response(status=500, text=str(exc), content_type="text/plain")

        if (DIST_DIR / "index.html").exists():
            return web.FileResponse(DIST_DIR / "index.html")
        return web.Response(
            status=500,
            text=(
                "Frontend build not found. Run `npm run build` from the repo root, "
                "or use `npm run dev` for the Vite development server."
            ),
            content_type="text/plain",
        )

    async def get_nodes(request: web.Request) -> web.Response:
        return web.Response(
            text=_dumps(get_all_node_info()),
            content_type="application/json",
        )

    async def list_files(request: web.Request) -> web.Response:
        session_id = require_session_id(request)
        input_path = session_input_dir(session_id)
        files = sorted(
            server_path_to_client_path(entry, session_id)
            for entry in input_path.iterdir()
            if entry.is_file() and not entry.name.startswith(".")
        ) if input_path.exists() else []
        return web.Response(text=_dumps(files), content_type="application/json")

    async def create_upload_folder(request: web.Request) -> web.Response:
        session_id = require_session_id(request)
        body = await request.json()
        relative_path = normalize_relative_upload_path(body.get("path", ""))
        target = session_input_dir(session_id) / Path(relative_path.as_posix())
        target.mkdir(parents=True, exist_ok=True)
        return web.Response(
            text=_dumps({"path": session_upload_uri(relative_path)}),
            content_type="application/json",
        )

    async def get_folder_files(request: web.Request) -> web.Response:
        from backend.nodes.helpers import list_folder_paths

        session_id = require_session_id(request)
        folder_path = request.query.get("folder", "")
        if not folder_path:
            return web.Response(text=_dumps([]), content_type="application/json")

        resolved_path = resolve_request_path(session_id, folder_path)
        running_loop = asyncio.get_running_loop()
        entries = await running_loop.run_in_executor(None, list_folder_paths, str(resolved_path))

        payload = []
        for entry in entries:
            mapped = dict(entry)
            if "path" in mapped:
                mapped["path"] = server_path_to_client_path(mapped["path"], session_id)
            payload.append(mapped)
        return web.Response(text=_dumps(payload), content_type="application/json")

    async def upload_file(request: web.Request) -> web.Response:
        session_id = require_session_id(request)
        reader = await request.multipart()
        relative_path = None
        filename = ""
        file_bytes = None

        while True:
            field = await reader.next()
            if field is None:
                break
            if field.name == "relative_path":
                relative_path = await field.text()
                continue
            if field.name == "file":
                filename = Path(field.filename or "upload.bin").name
                chunks = []
                while True:
                    chunk = await field.read_chunk(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                file_bytes = b"".join(chunks)

        if file_bytes is None:
            raise web.HTTPBadRequest(reason="Expected a 'file' field in multipart body")

        relative = normalize_relative_upload_path(relative_path or filename)
        dest = session_input_dir(session_id) / Path(relative.as_posix())
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(file_bytes)

        return web.Response(
            text=_dumps({"filename": filename, "path": session_upload_uri(relative)}),
            content_type="application/json",
        )

    async def upload_plugin(request: web.Request) -> web.Response:
        """
        Accept a .py plugin file, save it to plugins_dir(), hot-reload all
        plugins, and notify every connected WebSocket client to refresh /nodes.

        Warning: uploading Python files is equivalent to remote code execution.
        This endpoint is intentionally unrestricted because argonode is a
        local-first application; do not expose it on a public network.
        """
        reader = await request.multipart()
        filename = ""
        file_bytes = None

        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == "file":
                filename = Path(part.filename or "plugin.py").name
                chunks = []
                while True:
                    chunk = await part.read_chunk(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                file_bytes = b"".join(chunks)

        if file_bytes is None:
            raise web.HTTPBadRequest(reason="Expected a 'file' field in multipart body")
        if not filename.endswith(".py"):
            raise web.HTTPBadRequest(reason="Only .py plugin files are accepted")

        dest = plugins_dir() / filename
        dest.write_bytes(file_bytes)

        # Hot-reload: re-run the loader (handles re-import of changed files).
        load_plugins(plugins_dir())

        # Tell every connected frontend to re-fetch GET /nodes.
        msg = _dumps({"type": "nodes_updated"})
        for ws_set in session_websockets.values():
            for ws in list(ws_set):
                try:
                    await ws.send_str(msg)
                except Exception:
                    pass

        return web.Response(
            text=_dumps({"filename": filename, "loaded": True}),
            content_type="application/json",
        )

    async def download_file(request: web.Request) -> web.Response:
        body = await request.read()
        filename = request.query.get("filename", "workflow.png")
        return web.Response(
            body=body,
            content_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    async def save_workflow_png(request: web.Request) -> web.Response:
        body = await request.read()
        target_path = request.query.get("path", "")
        if not target_path:
            raise web.HTTPBadRequest(reason="Missing path")
        try:
            saved_path = save_png_bytes(target_path, body)
        except ValueError as exc:
            raise web.HTTPBadRequest(reason=str(exc)) from exc
        return web.Response(
            text=_dumps({"path": str(saved_path)}),
            content_type="application/json",
        )

    async def get_channels(request: web.Request) -> web.Response:
        from backend.nodes.helpers import list_channels

        session_id = require_session_id(request)
        filepath = request.query.get("file", "")
        if not filepath:
            return web.Response(
                text=_dumps([{"name": "field", "type": "DATA_FIELD"}]),
                content_type="application/json",
            )

        resolved_path = resolve_request_path(session_id, filepath)
        channels = await loop.run_in_executor(None, list_channels, str(resolved_path))
        return web.Response(text=_dumps(channels), content_type="application/json")

    async def submit_prompt(request: web.Request) -> web.Response:
        session_id = require_session_id(request)
        body = await request.json()
        prompt = body.get("prompt")
        if not isinstance(prompt, dict) or not prompt:
            raise web.HTTPBadRequest(reason="'prompt' must be a non-empty dict")

        normalized_prompt = rewrite_prompt_paths(prompt, session_id)
        prompt_id = new_prompt_id()
        engine = get_session_engine(session_id)

        async def run():
            broadcast(session_id, {"type": "execution_start", "data": {"prompt_id": prompt_id}})

            def on_start(node_id: str) -> None:
                broadcast(session_id, {"type": "executing", "data": {"node": node_id, "prompt_id": prompt_id}})

            def on_done(node_id: str, elapsed_ms: float) -> None:
                broadcast(session_id, {
                    "type": "node_timing",
                    "data": {"node_id": node_id, "elapsed_ms": elapsed_ms},
                })

            try:
                await loop.run_in_executor(
                    None,
                    lambda: engine.execute(
                        normalized_prompt,
                        on_node_start=on_start,
                        on_node_done=on_done,
                        on_preview=lambda node_id, payload: on_preview(session_id, node_id, payload),
                        on_table=lambda node_id, rows: on_table(session_id, node_id, rows),
                        on_mesh=lambda node_id, mesh_data: on_mesh(session_id, node_id, mesh_data),
                        on_overlay=lambda node_id, overlay_data: on_overlay(session_id, node_id, overlay_data),
                        on_value=lambda node_id, payload: on_value(session_id, node_id, payload),
                        on_warning=lambda node_id, message: on_warning(session_id, node_id, message),
                    ),
                )
                broadcast(session_id, {"type": "execution_complete", "data": {"prompt_id": prompt_id}})
            except Exception as exc:
                log.exception("Execution error")
                broadcast(session_id, {
                    "type": "execution_error",
                    "data": {"node_id": "", "message": str(exc)},
                })

        asyncio.ensure_future(run())
        return web.Response(
            text=_dumps({"prompt_id": prompt_id}),
            content_type="application/json",
        )

    async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
        session_id = require_session_id(request)
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        session_websockets[session_id].add(ws)
        log.info(
            "WebSocket client connected for session %s (%d total in session)",
            session_id,
            len(session_websockets[session_id]),
        )
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    pass
                elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
        finally:
            session_websockets[session_id].discard(ws)
            if not session_websockets[session_id]:
                session_websockets.pop(session_id, None)
            log.info(
                "WebSocket client disconnected for session %s (%d remaining in session)",
                session_id,
                len(session_websockets.get(session_id, ())),
            )
        return ws

    app = web.Application()
    app["allow_local_filesystem"] = allow_local_filesystem

    app.router.add_get("/", index)
    app.router.add_get("/nodes", get_nodes)
    app.router.add_get("/files", list_files)
    app.router.add_get("/folder-files", get_folder_files)
    app.router.add_post("/upload-folder", create_upload_folder)
    app.router.add_post("/upload", upload_file)
    if _plugins_on:
        app.router.add_post("/upload-plugin", upload_plugin)
    app.router.add_post("/download", download_file)
    app.router.add_post("/save-workflow-png", save_workflow_png)
    app.router.add_get("/channels", get_channels)
    app.router.add_post("/prompt", submit_prompt)
    app.router.add_get("/ws", websocket_handler)

    if (DIST_DIR / "assets").exists():
        app.router.add_static("/assets", DIST_DIR / "assets")
    if FRONTEND_DIR.exists():
        app.router.add_static("/static", FRONTEND_DIR)

    async def _cors_middleware(app_, handler):
        async def middleware(request):
            if request.method == "OPTIONS":
                return web.Response(headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": f"Content-Type, {SESSION_HEADER}",
                })
            response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response

        return middleware

    app.middlewares.append(_cors_middleware)
    return app
