"""
Exporter for IMAGE values (numpy arrays, ImageData annotation sources).

Images are raw pixel arrays — no physical calibration by design — so none of
the formats here round-trip dimensions. PNG/TIFF convert to uint8 via the
same image_to_uint8 helper the preview pipeline uses; NPZ preserves the raw
array.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from backend.data_types import image_to_uint8
from backend.exporters._base import FormatSpec

accepted_types: tuple[str, ...] = ("IMAGE", "ANNOTATION_SOURCE")

FORMATS: dict[str, FormatSpec] = {
    "PNG":  FormatSpec(ext=".png",  round_trip=False, label="PNG"),
    "TIFF": FormatSpec(ext=".tiff", round_trip=False, label="TIFF"),
    "NPZ":  FormatSpec(ext=".npz",  round_trip=False, label="NumPy (.npz)"),
}


def save(path: Path, value: np.ndarray, format_name: str, **_opts) -> None:
    arr = np.asarray(value)
    if format_name == "PNG":
        from PIL import Image
        Image.fromarray(image_to_uint8(arr)).save(str(path))
        return
    if format_name == "TIFF":
        import tifffile
        tifffile.imwrite(str(path), image_to_uint8(arr))
        return
    if format_name == "NPZ":
        np.savez(str(path), image=arr)
        return
    raise ValueError(f"Format {format_name!r} is not supported for IMAGE.")
