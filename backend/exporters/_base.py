"""
Base protocol for file exporters.

Each exporter module handles one tono value type (DATA_FIELD, IMAGE, LINE, …)
and implements one or more output formats. Registration is discovered via the
module-level attributes declared below, so adding a new exporter is a matter
of dropping a new file in this package and importing it from __init__.

A single file per value type (rather than per format) keeps format choices
that share plumbing — PNG & TIFF previews for DATA_FIELD, CSV & JSON for
tables — co-located, which is where most of the shared logic lives.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable


@dataclass(frozen=True)
class FormatSpec:
    """One output format supported by an exporter module."""

    #: File extension (leading dot), e.g. ".tiff".
    ext: str
    #: True if the format preserves enough information to reload the value
    #: via the matching importer. Advertised in the UI so users can tell
    #: "save a preview" and "save for later" apart.
    round_trip: bool
    #: Short human-readable label. The enum key used in the format dropdown
    #: is the dict key in each module's FORMATS map; `label` is what we'd
    #: surface in tooltips or docs. Leave empty to fall back to the key.
    label: str = ""


@runtime_checkable
class Exporter(Protocol):
    """Structural protocol satisfied by every module in backend.exporters."""

    #: Tono type names this exporter handles. Must match the upper-case names
    #: used in node INPUT_TYPES / OUTPUTS (e.g. "DATA_FIELD", "IMAGE", "LINE").
    accepted_types: tuple[str, ...]

    #: Format name → spec. Format names are what users pick in the Save node's
    #: format dropdown, so they should be short and recognizable.
    FORMATS: dict[str, FormatSpec]

    def save(self, path: Path, value: Any, format_name: str, **opts: Any) -> None:
        """Write *value* to *path* in *format_name*.

        The caller is responsible for ensuring ``path`` has the correct
        extension (see registry.resolve_path) and that ``value`` is of a type
        listed in ``accepted_types``.
        """
        ...


# Re-exported so modules can write `from backend.exporters._base import FormatSpec`.
__all__ = ["FormatSpec", "Exporter"]
