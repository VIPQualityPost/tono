from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import inspect
from typing import Any, Callable

Callback = Callable[[str, Any], None]

_callbacks_var: ContextVar[dict[str, Callback | None]] = ContextVar(
    "tono_execution_callbacks",
    default={},
)
_node_id_var: ContextVar[str | None] = ContextVar("tono_execution_node_id", default=None)

_LEGACY_CALLBACK_ATTRS = {
    "preview": "_broadcast_fn",
    "table": "_broadcast_table_fn",
    "mesh": "_broadcast_mesh_fn",
    "overlay": "_broadcast_overlay_fn",
    "value": "_broadcast_value_fn",
    "warning": "_broadcast_warning_fn",
}


@contextmanager
def execution_callbacks(
    *,
    preview: Callback | None = None,
    table: Callback | None = None,
    mesh: Callback | None = None,
    overlay: Callback | None = None,
    value: Callback | None = None,
    warning: Callback | None = None,
):
    token = _callbacks_var.set({
        "preview": preview,
        "table": table,
        "mesh": mesh,
        "overlay": overlay,
        "value": value,
        "warning": warning,
    })
    try:
        yield
    finally:
        _callbacks_var.reset(token)


@contextmanager
def active_node(node_id: str):
    token = _node_id_var.set(str(node_id))
    try:
        yield
    finally:
        _node_id_var.reset(token)


def current_node_id() -> str | None:
    return _node_id_var.get()


def _legacy_emit(kind: str, payload: Any) -> bool:
    callback_attr = _LEGACY_CALLBACK_ATTRS.get(kind)
    if not callback_attr:
        return False

    frame = inspect.currentframe()
    try:
        frame = frame.f_back
        while frame is not None:
            for owner_name in ("self", "cls"):
                owner = frame.f_locals.get(owner_name)
                if owner is None:
                    continue

                candidate = owner if isinstance(owner, type) else owner.__class__
                callback = getattr(candidate, callback_attr, None)
                node_id = getattr(candidate, "_current_node_id", None)
                if callback is not None and node_id:
                    callback(str(node_id), payload)
                    return True
            frame = frame.f_back
    finally:
        del frame

    return False


def _emit(kind: str, payload: Any) -> None:
    callbacks = _callbacks_var.get()
    callback = callbacks.get(kind)
    node_id = current_node_id()
    if callback is not None and node_id:
        callback(node_id, payload)
        return

    _legacy_emit(kind, payload)


def emit_preview(payload: Any) -> None:
    _emit("preview", payload)


def emit_table(rows: list) -> None:
    _emit("table", rows)


def emit_mesh(mesh: dict) -> None:
    _emit("mesh", mesh)


def emit_overlay(overlay: dict) -> None:
    _emit("overlay", overlay)


def emit_value(payload: Any) -> None:
    _emit("value", payload)


def emit_warning(message: str) -> None:
    _emit("warning", message)
