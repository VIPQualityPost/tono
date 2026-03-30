from __future__ import annotations

import threading
from pathlib import Path

import pytest

from backend.execution_context import active_node, emit_warning, execution_callbacks
from backend.session_runtime import (
    ensure_session_runtime_dirs,
    resolve_client_path,
    server_path_to_client_path,
    session_upload_uri,
)


def test_session_paths_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("TONO_APPDATA", str(tmp_path / "appdata"))

    session_id = "session-test-1234"
    input_dir, _ = ensure_session_runtime_dirs(session_id)
    target = input_dir / "picked-folder" / "image.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"png")

    client_path = session_upload_uri("picked-folder/image.png")
    resolved = resolve_client_path(client_path, session_id=session_id, allow_local_filesystem=False)

    assert resolved == target.resolve()
    assert server_path_to_client_path(target, session_id) == client_path


def test_browser_sessions_cannot_escape_workspace(monkeypatch, tmp_path):
    monkeypatch.setenv("TONO_APPDATA", str(tmp_path / "appdata"))

    session_id = "session-test-5678"
    ensure_session_runtime_dirs(session_id)

    outside_path = (tmp_path / "outside" / "secret.dat").resolve()

    with pytest.raises(PermissionError):
        resolve_client_path(str(outside_path), session_id=session_id, allow_local_filesystem=False)


def test_execution_callbacks_are_thread_local():
    results = []
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def worker(label: str):
        def on_warning(node_id: str, message: str):
            with lock:
                results.append((label, node_id, message))

        with execution_callbacks(warning=on_warning):
            with active_node(f"node-{label}"):
                barrier.wait(timeout=5)
                emit_warning(f"warning-{label}")

    threads = [
        threading.Thread(target=worker, args=("a",)),
        threading.Thread(target=worker, args=("b",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert sorted(results) == [
        ("a", "node-a", "warning-a"),
        ("b", "node-b", "warning-b"),
    ]
