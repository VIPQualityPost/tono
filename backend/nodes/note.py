from __future__ import annotations

import re

from backend.node_registry import register_node
from backend.data_types import DataTable
from backend.nodes.helpers import _resolve_path, _import_ibw_loader


def _parse_ibw_note(note_bytes: bytes) -> list[dict]:
    try:
        text = note_bytes.decode("utf-8", errors="replace")
    except Exception:
        return []

    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r'^([^:=]+)[=:](.+)$', line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if not key:
            continue
        rows.append({"key": key, "value": value})

    return rows


@register_node(display_name="IBW Note")
class IBWNote:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("FILE_PICKER", {"default": "", "hide_when_input_connected": "path"}),
            },
            "optional": {
                "path": ("FILE_PATH", {"label": "path"}),
            },
        }

    OUTPUTS = (
        ('DATA_TABLE', 'note'),
    )
    FUNCTION = "load"

    DESCRIPTION = (
        "Read the Note metadata from an .ibw file and display all entries "
        "as a table of key/value pairs."
    )

    def load(self, filename: str = "", path: str | None = None) -> tuple:
        selected = str(path).strip() if path is not None else str(filename).strip()
        if not selected:
            raise ValueError("No file selected.")
        path_obj = _resolve_path(selected)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path_obj}")
        if path_obj.suffix.lower() != ".ibw":
            raise ValueError(f"Expected an .ibw file, got: {path_obj.suffix}")

        load_ibw = _import_ibw_loader()
        wave = load_ibw(str(path_obj))
        note_bytes = wave["wave"].get("note", b"") or b""

        rows = _parse_ibw_note(note_bytes)
        if not rows:
            raise ValueError("No metadata found in the .ibw note.")

        return (DataTable(rows),)
