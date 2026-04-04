"""
aiohttp web server for tono.

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
import os
import re
import secrets
import shutil
import sys
import time
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
    session_root_dir,
    session_upload_uri,
    validate_session_id,
)

log = logging.getLogger(__name__)

FRONTEND_DIR = frontend_dir()
DIST_DIR = frontend_dist_dir()
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

GITHUB_REPO = "vipqualitypost/tono"
_APP_VERSION: str | None = None


def _get_app_version() -> str:
    global _APP_VERSION
    if _APP_VERSION is not None:
        return _APP_VERSION
    try:
        import tomllib
        with open(project_root() / "pyproject.toml", "rb") as f:
            _APP_VERSION = tomllib.load(f)["project"]["version"]
    except Exception:
        _APP_VERSION = "0.0.0"
    return _APP_VERSION


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

    from backend.execution import ExecutionEngine, NodeExecutionError, new_prompt_id
    from backend.node_registry import NODE_CLASS_MAPPINGS, get_all_node_info

    ensure_runtime_dirs(with_plugins=_plugins_on)

    session_engines: dict[str, ExecutionEngine] = {}
    session_websockets: dict[str, set[web.WebSocketResponse]] = defaultdict(set)
    pending_downloads: dict[str, Path] = {}
    _last_download_token: dict[str, str] = {}  # session_id → token (limit one per session)
    _prompt_last_time: dict[str, float] = {}   # session_id → monotonic timestamp
    _pending_cleanups: dict[str, asyncio.TimerHandle] = {}  # session_id → scheduled cleanup
    PROMPT_MIN_INTERVAL = 0.5  # seconds between /prompt submissions per session
    SESSION_TTL = int(os.getenv("TONO_SESSION_TTL", "60"))  # seconds after last WS disconnect

    def _is_link(value) -> bool:
        return (
            isinstance(value, (list, tuple))
            and len(value) == 2
            and isinstance(value[0], str)
            and isinstance(value[1], int)
        )

    async def health_check(_request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

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

    def on_file_download(session_id: str, node_id: str, file_path: str) -> None:
        token = secrets.token_urlsafe(16)
        path = Path(file_path)
        # Evict the previous pending download for this session (limit one).
        prev_token = _last_download_token.pop(session_id, None)
        if prev_token:
            pending_downloads.pop(prev_token, None)
        pending_downloads[token] = path
        _last_download_token[session_id] = token
        broadcast(session_id, {"type": "file_download", "data": {"node_id": node_id, "token": token, "filename": path.name}})

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

    async def get_help_docs(request: web.Request) -> web.Response:
        public_dir = FRONTEND_DIR / "public"
        if not public_dir.is_dir():
            return web.json_response([])
        files = sorted(p.name for p in public_dir.iterdir() if p.suffix.lower() == ".md" and p.is_file())
        result = []
        for fname in files:
            text = (public_dir / fname).read_text(encoding="utf-8", errors="replace")
            title = fname.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
            result.append({"title": title, "content": text})
        return web.json_response(result)

    async def get_help_doc_file(request: web.Request) -> web.Response:
        filename = request.match_info["filename"]
        public_dir = FRONTEND_DIR / "public"
        path = (public_dir / filename).resolve()
        if not str(path).startswith(str(public_dir.resolve())) or not path.is_file():
            return web.Response(status=404, text="Not found")
        text = path.read_text(encoding="utf-8", errors="replace")
        title = filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
        return web.json_response({"title": title, "content": text})

    async def get_nodes(request: web.Request) -> web.Response:
        return web.Response(
            text=_dumps(get_all_node_info()),
            content_type="application/json",
        )

    async def get_node_doc(request: web.Request) -> web.Response:
        name = request.rel_url.query.get("name", "").strip()
        if not name:
            raise web.HTTPBadRequest(reason="Missing 'name' query parameter")
        docs_dir = project_root() / "docs" / "nodes"
        # Try exact match first, then fall back to replacing " / " with "-"
        candidates = [docs_dir / f"{name}.md", docs_dir / f"{name.replace(' / ', '-')}.md"]
        for path in candidates:
            if path.exists() and path.is_file():
                return web.Response(text=path.read_text(encoding="utf-8"), content_type="text/plain")
        raise web.HTTPNotFound(reason=f"No documentation found for '{name}'")

    async def list_files(request: web.Request) -> web.Response:
        session_id = require_session_id(request)
        input_path = session_input_dir(session_id)
        files = sorted(
            server_path_to_client_path(entry, session_id)
            for entry in input_path.iterdir()
            if entry.is_file() and not entry.name.startswith(".")
        ) if input_path.exists() else []
        return web.Response(text=_dumps(files), content_type="application/json")

    async def get_file_content(request: web.Request) -> web.Response:
        session_id = require_session_id(request)
        path_value = request.query.get("path", "")
        if not path_value:
            raise web.HTTPBadRequest(reason="Missing 'path' query parameter")
        resolved = resolve_request_path(session_id, path_value)
        if not resolved.is_file():
            raise web.HTTPNotFound(reason=f"File not found: {path_value}")
        return web.FileResponse(resolved)

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
        This endpoint is intentionally unrestricted because tono is a
        local-first application; do not expose it on a public network.
        """
        if not _plugins_on:
            raise web.HTTPForbidden(
                reason="Plugin upload is disabled. "
                       "Set TONO_PLUGINS=1 to enable (allows arbitrary code execution).",
            )
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

    def _sanitize_filename(name: str, fallback: str = "download") -> str:
        """Strip path separators and control characters from a filename."""
        clean = re.sub(r'[/\\:\x00-\x1f\x7f"*?<>|]', '_', str(name).strip())
        return clean or fallback

    async def download_file(request: web.Request) -> web.Response:
        body = await request.read()
        filename = _sanitize_filename(request.query.get("filename", "workflow.png"), "workflow.png")
        return web.Response(
            body=body,
            content_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    async def download_saved_file(request: web.Request) -> web.Response:
        token = request.match_info["token"]
        path = pending_downloads.pop(token, None)
        if path is None or not path.is_file():
            raise web.HTTPNotFound(reason="File not found")
        filename = _sanitize_filename(path.name, "download")
        return web.FileResponse(
            path,
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

        now = time.monotonic()
        last = _prompt_last_time.get(session_id, 0.0)
        if now - last < PROMPT_MIN_INTERVAL:
            raise web.HTTPTooManyRequests(
                reason="Please wait before submitting another prompt",
            )
        _prompt_last_time[session_id] = now

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
                        on_file_download=lambda node_id, file_path: on_file_download(session_id, node_id, file_path),
                    ),
                )
                broadcast(session_id, {"type": "execution_complete", "data": {"prompt_id": prompt_id}})
            except NodeExecutionError as exc:
                log.exception("Execution error on node %s", exc.node_id)
                broadcast(session_id, {
                    "type": "execution_error",
                    "data": {"node_id": exc.node_id, "message": str(exc)},
                })
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

    def _cleanup_session(session_id: str) -> None:
        """Evict all server-side state for a session after its grace period."""
        _pending_cleanups.pop(session_id, None)
        # If the session reconnected during the grace period, abort cleanup
        if session_websockets.get(session_id):
            return
        session_engines.pop(session_id, None)
        _prompt_last_time.pop(session_id, None)
        prev_token = _last_download_token.pop(session_id, None)
        if prev_token:
            pending_downloads.pop(prev_token, None)
        session_dir = session_root_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)
        log.info("Cleaned up session %s", session_id)

    async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
        session_id = require_session_id(request)
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        session_websockets[session_id].add(ws)
        # Cancel any pending cleanup for this session (user reconnected)
        handle = _pending_cleanups.pop(session_id, None)
        if handle is not None:
            handle.cancel()
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
                # Schedule cleanup after grace period
                if SESSION_TTL > 0:
                    _pending_cleanups[session_id] = loop.call_later(
                        SESSION_TTL, _cleanup_session, session_id,
                    )
            log.info(
                "WebSocket client disconnected for session %s (%d remaining in session)",
                session_id,
                len(session_websockets.get(session_id, ())),
            )
        return ws

    async def check_update(_request: web.Request) -> web.Response:
        import aiohttp as _aiohttp

        current = _get_app_version()
        if os.getenv("TONO_UPDATE_CHECK", "").strip().lower() in ("off", "0", "false", "no"):
            return web.json_response({"current": current, "latest": None, "update_available": False})
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        try:
            async with _aiohttp.ClientSession() as session:
                async with session.get(url, timeout=_aiohttp.ClientTimeout(total=5),
                                       headers={"Accept": "application/vnd.github.v3+json"}) as resp:
                    if resp.status != 200:
                        return web.json_response({"current": current, "latest": None, "update_available": False})
                    data = await resp.json()
            latest = str(data.get("tag_name", "")).lstrip("vV")
            html_url = str(data.get("html_url", ""))
            update_available = latest != "" and latest != current
            return web.json_response({
                "current": current,
                "latest": latest,
                "update_available": update_available,
                "url": html_url,
            })
        except Exception:
            return web.json_response({"current": current, "latest": None, "update_available": False})

    app = web.Application(client_max_size=100 * 1024 * 1024)  # 100 MB upload cap
    app["allow_local_filesystem"] = allow_local_filesystem

    app.router.add_get("/health", health_check)
    app.router.add_get("/", index)
    app.router.add_get("/nodes", get_nodes)
    app.router.add_get("/files", list_files)
    app.router.add_get("/folder-files", get_folder_files)
    app.router.add_post("/upload-folder", create_upload_folder)
    app.router.add_post("/upload", upload_file)
    app.router.add_post("/upload-plugin", upload_plugin)
    app.router.add_post("/download", download_file)
    app.router.add_post("/save-workflow-png", save_workflow_png)
    app.router.add_get("/channels", get_channels)
    app.router.add_get("/docs", get_node_doc)
    app.router.add_get("/file-content", get_file_content)
    app.router.add_get("/help-docs", get_help_docs)
    app.router.add_get("/help-docs/{filename}", get_help_doc_file)
    app.router.add_post("/prompt", submit_prompt)
    app.router.add_get("/download-save/{token}", download_saved_file)
    app.router.add_get("/check-update", check_update)
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
