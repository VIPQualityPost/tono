from __future__ import annotations
import re
import numpy as np
from pathlib import Path

from backend.node_registry import register_node
from backend.execution_context import emit_warning, emit_file_download
from backend.data_types import DataField, image_to_uint8
from backend.nodes.helpers import _MAX_SAVE_FIELDS


@register_node(display_name="Save Layers")
class SaveImage:
    @classmethod
    def INPUT_TYPES(cls):
        optional = {
            "directory": ("DIRECTORY", {"label": "directory"}),
        }
        for i in range(_MAX_SAVE_FIELDS):
            optional[f"field_{i}"] = ("DATA_FIELD", {
                "label": f"layer {i + 1}",
                "accepted_types": ["IMAGE", "ANNOTATION_SOURCE"],
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
                "directory_path": ("STRING", {
                    "default": "",
                    "label": "directory",
                    "placeholder": "directory (optional, desktop only)",
                    "placement": "top",
                    "hide_when_input_connected": "directory",
                    "top_socket_input": "directory",
                    }),
                "format": (["TIFF", "NPZ"],),
            },
            "optional": optional,
        }

    OUTPUTS = ()
    FUNCTION = "save"

    OUTPUT_NODE = True
    MANUAL_TRIGGER = True
    DESCRIPTION = (
        "Save one or more image/field layers to a single file. "
        "Each layer input accepts either a DATA_FIELD or an IMAGE, including annotated images. "
        "Optionally drive the output directory from a folder/path node, while keeping the filename widget for the file name. "
        "A new slot appears as each one is filled, with a matching per-layer name field. "
        "Use this for composing multi-channel stacks. TIFF writes multi-page data and stores layer names as page descriptions; "
        "NPZ writes named arrays using those layer names as keys. "
        "Click Save to write (does not auto-run)."
    )

    _broadcast_warning_fn = None
    _current_node_id = None

    def save(
        self,
        filename: str,
        directory_path: str = "",
        format: str = "TIFF",
        directory: str | None = None,
        **kwargs,
    ):
        layers = []
        layer_names = []
        for i in range(_MAX_SAVE_FIELDS):
            layer = kwargs.get(f"field_{i}")
            if layer is not None:
                layers.append(layer)
                layer_names.append(self._resolve_layer_name(kwargs.get(f"layer_name_{i}"), i))

        if not layers:
            raise ValueError("No layers connected — connect at least one DATA_FIELD or IMAGE input.")

        path = self._resolve_save_path(filename, format, directory, directory_path)

        if format == "TIFF":
            self._save_tiff(path, layers, layer_names)
        else:
            self._save_npz(path, layers, layer_names)

        self._send_warning(f"Saved {len(layers)} layer(s) to {path.name}")
        emit_file_download(str(path))
        return ()

    def _save_tiff(self, path: Path, layers: list[DataField | np.ndarray], layer_names: list[str]):
        import tifffile

        with tifffile.TiffWriter(str(path)) as tif:
            for layer, layer_name in zip(layers, layer_names):
                tif.write(self._layer_array_for_tiff(layer), description=layer_name)

    def _save_npz(self, path: Path, layers: list[DataField | np.ndarray], layer_names: list[str]):
        arrays = {}
        used_keys = set()
        for i, (layer, layer_name) in enumerate(zip(layers, layer_names)):
            arrays[self._unique_npz_key(layer_name, used_keys, i)] = self._layer_array_for_npz(layer)
        np.savez(str(path), **arrays)

    def _resolve_layer_name(self, raw_name: object, index: int) -> str:
        text = str(raw_name).strip() if raw_name is not None else ""
        return text or f"layer_{index}"

    def _resolve_save_path(
        self,
        filename: str,
        format: str,
        directory: str | None,
        directory_path: str = "",
    ) -> Path:
        ext = ".tiff" if format == "TIFF" else ".npz"
        raw_filename = str(filename).strip() if filename is not None else ""
        raw_directory = str(directory).strip() if directory is not None else ""
        if not raw_directory:
            raw_directory = str(directory_path).strip() if directory_path is not None else ""

        if raw_directory:
            dir_path = Path(raw_directory).expanduser()
            if dir_path.exists() and not dir_path.is_dir():
                raise ValueError("Directory input expects a folder path, not a file path.")
            if not dir_path.exists():
                if dir_path.suffix:
                    raise ValueError("Directory input expects a folder path, not a file path.")
                dir_path.mkdir(parents=True, exist_ok=True)

            filename_part = Path(raw_filename).name if raw_filename else ""
            if not filename_part:
                raise ValueError("No output filename selected — enter a file name when using a directory input.")
            path = dir_path / filename_part
        else:
            if not raw_filename:
                raise ValueError("No output filename selected — enter a file name.")
            candidate = Path(raw_filename).expanduser()
            if candidate.is_absolute():
                candidate.parent.mkdir(parents=True, exist_ok=True)
                path = candidate
            else:
                from backend.nodes.save import DOWNLOAD_DIR
                DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
                path = DOWNLOAD_DIR / candidate.name

        if path.suffix.lower() != ext:
            path = path.with_suffix(ext)
        return path

    def _unique_npz_key(self, raw_name: str, used_keys: set[str], index: int) -> str:
        key = re.sub(r"[^0-9A-Za-z_]+", "_", str(raw_name).strip()).strip("_")
        if not key:
            key = f"layer_{index}"
        if key[0].isdigit():
            key = f"layer_{key}"

        candidate = key
        suffix = 2
        while candidate in used_keys:
            candidate = f"{key}_{suffix}"
            suffix += 1
        used_keys.add(candidate)
        return candidate

    def _layer_array_for_tiff(self, layer: DataField | np.ndarray) -> np.ndarray:
        if isinstance(layer, DataField):
            return np.asarray(layer.data, dtype=np.float32)
        if isinstance(layer, np.ndarray):
            return image_to_uint8(layer)
        raise ValueError(f"Unsupported save layer type: {type(layer).__name__}")

    def _layer_array_for_npz(self, layer: DataField | np.ndarray) -> np.ndarray:
        if isinstance(layer, DataField):
            return np.asarray(layer.data)
        if isinstance(layer, np.ndarray):
            return np.asarray(layer)
        raise ValueError(f"Unsupported save layer type: {type(layer).__name__}")

    def _send_warning(self, message: str):
        emit_warning(message)

        return ()
