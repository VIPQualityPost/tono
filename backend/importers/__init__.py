"""
File importer registry.

Each module in this package exposes:
  extensions   frozenset[str]       - lower-case extensions it handles
  calibrated   bool                 - True when physical dimensions are known
  load(path)   → list[DataField]    - load all channels
  channel_names(path) → list[str]   - channel name strings (same order as load)

Usage::

    from backend.importers import get_importer, all_extensions

    importer = get_importer(".gwy")   # returns the gwy module, or None
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

from backend.importers import array_image, ergo_hdf5, gwy, ibw, sxm

_IMPORTERS: list[ModuleType] = [gwy, sxm, ibw, ergo_hdf5, array_image]

# ext → importer module
_REGISTRY: dict[str, ModuleType] = {}
for _mod in _IMPORTERS:
    for _ext in _mod.extensions:
        _REGISTRY[_ext] = _mod


def get_importer(ext: str) -> ModuleType | None:
    """Return the importer module for *ext* (e.g. '.gwy'), or None."""
    return _REGISTRY.get(ext.lower())


def all_extensions() -> frozenset[str]:
    """All file extensions supported across every registered importer."""
    return frozenset(_REGISTRY)


def calibrated_extensions() -> frozenset[str]:
    """Extensions whose importers report physical calibration."""
    return frozenset(ext for ext, mod in _REGISTRY.items() if mod.calibrated)
