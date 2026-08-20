from __future__ import annotations
from functools import lru_cache
from pathlib import Path

from backend.node_registry import register_node
from backend.execution_context import emit_warning
from backend.data_types import COLORMAPS, DataField, resolve_colormap_input
from backend.importers import get_importer, calibrated_extensions


@register_node(display_name="Image")
class Image:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("FILE_PICKER", {"default": "", "hide_when_input_connected": "path"}),
                "colormap": (list(COLORMAPS), {"hide_when_input_connected": "colormap_map"}),
            },
            "optional": {
                "colormap_map": ("COLORMAP", {"label": "colormap"}),
                "path": ("FILE_PATH", {"label": "path"}),
            },
        }

    OUTPUTS = (
        ("FILE_PATH", 'path'),
        ('DATA_FIELD', 'field'),
        ('DATA_FIELD', 'channel_2'),
        ('DATA_FIELD', 'channel_3'),
    )
    FUNCTION = "load"

    DESCRIPTION = (
        "Load any supported file. "
        "SPM and HDF5 provide calibrated dimensions; "
        "each channel gets its own output. "
        "Images and arrays are loaded as uncalibrated fields."
    )

    KEYWORDS = ("load", "open", "file", "import", "gwy", "sxm", "ibw", "png", "tiff", "npy", "hdf5")

    def load(self, filename: str = "", colormap: str = "viridis", colormap_map=None, path: str | None = None):
        selected_path = str(path).strip() if path is not None else str(filename).strip()
        if not selected_path:
            raise ValueError("No file selected — use Browse to pick a file.")
        path_obj = Path(selected_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path_obj}")
        if path_obj.is_dir():
            raise IsADirectoryError(f"Expected a file, got a directory: {path_obj}")

        ext = path_obj.suffix.lower()
        resolved_colormap = resolve_colormap_input(colormap, colormap_input=colormap_map, default="viridis")
        stat = path_obj.stat()
        cached_fields = Image._load_fields_cached(
            str(path_obj.resolve()),
            int(stat.st_mtime_ns),
            int(stat.st_size),
        )
        fields = tuple(field.copy() for field in cached_fields)

        for field in fields:
            field.colormap = resolved_colormap

        if ext not in calibrated_extensions():
            emit_warning("Uncalibrated data — no physical dimensions.")

        return (str(path_obj.resolve()),) + fields

    @staticmethod
    @lru_cache(maxsize=32)
    def _load_fields_cached(path_str: str, mtime_ns: int, size_bytes: int) -> tuple[DataField, ...]:
        path = Path(path_str)
        ext = path.suffix.lower()
        importer = get_importer(ext)
        if importer is None:
            raise ValueError(f"Unsupported file format: {ext}")
        return tuple(importer.load(path))
