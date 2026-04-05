from __future__ import annotations

import tempfile
from pathlib import Path

from backend.node_registry import register_node
from backend.execution_context import emit_warning, emit_file_download
from backend.exporters import (
    available_formats,
    get_exporter,
    resolve_path,
    type_name_for_value,
)

DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "tono-downloads"


def _choices_by_source_type() -> dict[str, list[str]]:
    """Build the format dropdown's source-type map from the exporter registry.

    Centralising this here means adding a new exporter module (or a new format
    inside an existing one) automatically surfaces in the UI — no parallel
    list to keep in sync.
    """
    return {
        "DATA_FIELD":        available_formats("DATA_FIELD"),
        "IMAGE":             available_formats("IMAGE"),
        "ANNOTATION_SOURCE": available_formats("ANNOTATION_SOURCE"),
        "LINE":              available_formats("LINE"),
        "RECORD_TABLE":      available_formats("RECORD_TABLE"),
        "DATA_TABLE":        available_formats("DATA_TABLE"),
        "FLOAT":             available_formats("FLOAT"),
        "MESH_MODEL":        available_formats("MESH_MODEL"),
    }


@register_node(display_name="Save")
class Save:
    @classmethod
    def INPUT_TYPES(cls):
        choices = _choices_by_source_type()
        return {
            "required": {
                "filename": ("STRING", {
                    "default": "",
                    "placeholder": "filename",
                    "placement": "top",
                }),
                "value": ("DATA_FIELD", {
                    "label": "value",
                    "accepted_types": [
                        "IMAGE",
                        "ANNOTATION_SOURCE",
                        "LINE",
                        "RECORD_TABLE",
                        "DATA_TABLE",
                        "MESH_MODEL",
                        "FLOAT",
                    ],
                }),
                "format": ("STRING", {
                    "default": choices["DATA_FIELD"][0] if choices["DATA_FIELD"] else "",
                    "choices_by_source_type": choices,
                    "source_type_input": "value",
                }),
            },
            "optional": {
                "plot_title": ("STRING", {
                    "default": "",
                    "placeholder": "plot title (optional)",
                    "label": "title",
                    "show_when_source_type": {"value": ["LINE"]},
                }),
            },
        }

    OUTPUTS = ()
    FUNCTION = "save"

    OUTPUT_NODE = True
    MANUAL_TRIGGER = True
    DESCRIPTION = (
        "Save a single graph value to disk. Supports fields, images, lines, tables, scalars, "
        "and 3D meshes. Use 'GWY' or 'TIFF (data)' for DataFields you want to re-open later "
        "with their physical units preserved."
    )

    KEYWORDS = ("export", "write", "download", "png", "tiff", "csv", "json", "npz", "obj", "stl", "gwy")

    def save(
        self,
        filename: str,
        format: str,
        value,
        plot_title: str = "",
    ):
        type_name = type_name_for_value(value)
        module, spec = get_exporter(type_name, format)
        path = resolve_path(filename, spec, DOWNLOAD_DIR)
        module.save(path, value, format, plot_title=plot_title)

        emit_warning(f"Saved to {path.name}")
        emit_file_download(str(path))
        return ()
