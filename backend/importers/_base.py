"""
Base protocol for file importers.

Each importer handles one or more file extensions and implements:
  load(path)          → list[DataField]
  channel_names(path) → list[str]   (optional, falls back to generic names)
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from backend.data_types import DataField


@runtime_checkable
class FileImporter(Protocol):
    #: File extensions this importer handles, e.g. {".gwy"}
    extensions: frozenset[str]

    #: True when physical dimensions are known (suppresses "uncalibrated" warning)
    calibrated: bool

    def load(self, path: Path) -> list[DataField]:
        """Load all channels from *path* and return them as DataField objects."""
        ...

    def channel_names(self, path: Path) -> list[str]:
        """Return channel name strings in the same order as load()."""
        ...
