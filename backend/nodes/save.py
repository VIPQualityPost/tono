from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from backend.node_registry import register_node
from backend.execution_context import emit_warning, emit_file_download
from backend.exporters import (
    available_formats,
    get_exporter,
    resolve_path,
    type_name_for_value,
)
from backend.nodes.helpers import _MAX_SAVE_FIELDS

DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "tono-downloads"

# Source types that expand into a layer stack (i.e., the Save node grows
# extra field_N inputs). Any other type (FLOAT, LINE, MESH, …) is a single
# value; no stacking UI is shown.
_STACKABLE_SOURCE_TYPES: tuple[str, ...] = ("DATA_FIELD", "IMAGE", "ANNOTATION_SOURCE")


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

        optional: dict[str, Any] = {
            "plot_title": ("STRING", {
                "default": "",
                "placeholder": "plot title (optional)",
                "label": "title",
                "show_when_source_type": {"value": ["LINE"]},
            }),
            # Name widget for the primary (value) layer. Only surfaces once
            # the stack grows beyond one layer, so single-value saves stay
            # clutter-free.
            "primary_name": ("STRING", {
                "default": "",
                "placeholder": "name",
                "show_when_input_visible": "field_0",
                "inline_with_input": "layer_1",
                "hide_label": True,
            }),
        }
        # Extra layer sockets for stackable source types. The frontend
        # progressive-reveal block keys off `field_N` and only shows slot N
        # once slot N-1 is connected; we further gate every slot on `value`
        # being a stackable source type via `show_when_source_type`.
        for i in range(_MAX_SAVE_FIELDS):
            optional[f"field_{i}"] = ("DATA_FIELD", {
                "label": f"layer {i + 2}",  # primary is layer 1
                "accepted_types": ["IMAGE", "ANNOTATION_SOURCE"],
                "show_when_source_type": {"value": list(_STACKABLE_SOURCE_TYPES)},
            })
            optional[f"layer_name_{i}"] = ("STRING", {
                "default": "",
                "placeholder": "name",
                "show_when_input_visible": f"field_{i}",
                "inline_with_input": f"field_{i}",
                "hide_label": True,
            })

        return {
            "required": {
                "filename": ("STRING", {
                    "default": "",
                    "placeholder": "filename",
                    "placement": "top",
                }),
                "value": ("DATA_FIELD", {
                    "label": "layer 1",
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
            "optional": optional,
        }

    OUTPUTS = ()
    FUNCTION = "save"

    OUTPUT_NODE = True
    MANUAL_TRIGGER = True
    DESCRIPTION = (
        "Save one or more channels."
        "Use 'GWY','TIFF (data)', or 'HDF5' when you need to re-open the result with its "
        "physical units preserved."
    )

    KEYWORDS = (
        "export", "write", "download", "png", "tiff", "csv", "json", "npz",
        "obj", "stl", "gwy", "hdf5", "layers", "stack", "channels",
    )

    def save(
        self,
        filename: str,
        format: str,
        value,
        plot_title: str = "",
        primary_name: str = "",
        **kwargs,
    ):
        type_name = type_name_for_value(value)
        module, spec = get_exporter(type_name, format)
        path = resolve_path(filename, spec, DOWNLOAD_DIR)

        extra_layers, layer_names = self._collect_extra_layers(
            type_name, primary_name, kwargs,
        )

        module.save(
            path,
            value,
            format,
            plot_title=plot_title,
            extra_layers=extra_layers,
            layer_names=layer_names,
        )

        emit_warning(f"Saved to {path.name}")
        emit_file_download(str(path))
        return ()

    def _collect_extra_layers(
        self,
        type_name: str,
        primary_name: str,
        kwargs: dict[str, Any],
    ) -> tuple[list[Any], list[str]]:
        """Pull field_N + layer_name_N from kwargs into parallel lists.

        Only applies when the primary value is a stackable source type; for
        anything else (LINE, FLOAT, MESH_MODEL, tables) any stray field_N
        kwargs are ignored — the frontend hides those sockets in that case
        and the backend treats it as a single-value save.
        """
        if type_name not in _STACKABLE_SOURCE_TYPES:
            return [], []

        extras: list[Any] = []
        extra_names: list[str] = []
        # Preserve the on-node order: iterate field_0, field_1, …, stopping at
        # the first hole. An unconnected slot in the middle would be a UI bug,
        # but bailing early keeps the saved stack matching what the user sees.
        for i in range(_MAX_SAVE_FIELDS):
            layer = kwargs.get(f"field_{i}")
            if layer is None:
                break
            extras.append(layer)
            extra_names.append(str(kwargs.get(f"layer_name_{i}", "") or "").strip())

        if not extras:
            return [], []

        # Full names list starts with the primary's name (empty → exporter
        # substitutes path.stem) and then each extra in order.
        names = [str(primary_name or "").strip(), *extra_names]
        return extras, names
