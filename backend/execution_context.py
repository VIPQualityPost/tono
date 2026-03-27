from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable

Callback = Callable[[str, Any], None]

_callbacks_var: ContextVar[dict[str, Callback | None]] = ContextVar(
    "argonode_execution_callbacks",
    default={},
)
_node_id_var: ContextVar[str | None] = ContextVar("argonode_execution_node_id", default=None)


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


def _emit(kind: str, payload: Any) -> None:
    callbacks = _callbacks_var.get()
    callback = callbacks.get(kind)
    node_id = current_node_id()
    if callback is not None and node_id:
        callback(node_id, payload)


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
