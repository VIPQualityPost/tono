"""
Lightweight node usage tracker.

Persists per-node execution counts and total execution time to a JSON file
in the app data directory. Thread-safe for concurrent prompt execution.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from backend.runtime_paths import app_data_dir

log = logging.getLogger(__name__)

_FLUSH_INTERVAL = 30  # seconds between disk writes
_STATS_FILENAME = "usage_stats.json"


class UsageTracker:
    """Accumulates node execution counts and periodically flushes to disk."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._path = app_data_dir() / _STATS_FILENAME
        self._dirty = False
        self._last_flush = 0.0
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, class_name: str, elapsed_ms: float) -> None:
        """Record one execution of *class_name*."""
        with self._lock:
            entry = self._data.get(class_name)
            if entry is None:
                entry = {"count": 0, "total_ms": 0.0}
                self._data[class_name] = entry
            entry["count"] += 1
            entry["total_ms"] += elapsed_ms
            self._dirty = True

        # Flush periodically (non-blocking — skip if another thread is writing)
        now = time.monotonic()
        if now - self._last_flush >= _FLUSH_INTERVAL:
            self._try_flush()

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """Return a copy of the current stats."""
        with self._lock:
            return {k: dict(v) for k, v in self._data.items()}

    def flush(self) -> None:
        """Force write to disk."""
        self._try_flush(force=True)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, value in raw.items():
                    if isinstance(value, dict) and "count" in value:
                        self._data[key] = {
                            "count": int(value["count"]),
                            "total_ms": float(value.get("total_ms", 0.0)),
                        }
            log.info("Loaded usage stats: %d nodes tracked", len(self._data))
        except Exception:
            log.warning("Could not load usage stats from %s — starting fresh", self._path)

    def _try_flush(self, *, force: bool = False) -> None:
        with self._lock:
            if not self._dirty and not force:
                return
            snapshot = {k: dict(v) for k, v in self._data.items()}
            self._dirty = False
            self._last_flush = time.monotonic()

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(snapshot, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            tmp.replace(self._path)
        except Exception:
            log.warning("Failed to write usage stats", exc_info=True)


# Module-level singleton — lazily created on first import via init().
_tracker: UsageTracker | None = None


def init() -> UsageTracker:
    """Create (or return existing) global tracker."""
    global _tracker
    if _tracker is None:
        _tracker = UsageTracker()
    return _tracker


def record(class_name: str, elapsed_ms: float) -> None:
    """Record one execution. No-op if tracker not initialised."""
    if _tracker is not None:
        _tracker.record(class_name, elapsed_ms)


def snapshot() -> dict[str, dict[str, Any]]:
    """Return current stats snapshot. Empty dict if not initialised."""
    if _tracker is not None:
        return _tracker.snapshot()
    return {}


def flush() -> None:
    """Flush to disk. No-op if tracker not initialised."""
    if _tracker is not None:
        _tracker.flush()
