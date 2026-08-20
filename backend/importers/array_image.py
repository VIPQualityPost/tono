"""
Importer for pixel images (PNG, TIFF, JPEG, BMP) and NumPy arrays (.npy, .npz).
These formats carry no physical calibration, so calibrated = False.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from backend.data_types import DataField


extensions = frozenset({".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".npy", ".npz"})
calibrated = False


def _as_gray_field(arr: np.ndarray) -> DataField:
    arr = np.asarray(arr)
    if arr.dtype != np.uint8:
        arr = arr.astype(np.float64)
    if arr.ndim == 3:
        # Drop the alpha plane: RGB(A) should average color channels only;
        # including alpha washes the grey conversion out.
        gray = np.mean(arr[..., :3].astype(np.float64), axis=2)
    else:
        gray = np.asarray(arr, dtype=np.float64)
    return DataField(data=gray)


def load(path: Path) -> list[DataField]:
    ext = path.suffix.lower()

    if ext == ".npy":
        return [_as_gray_field(np.load(str(path)))]
    if ext == ".npz":
        with np.load(str(path)) as npz:
            fields = [_as_gray_field(npz[key]) for key in npz.files]
        if not fields:
            raise ValueError(f"No arrays found in {path.name}")
        return fields

    from PIL import Image as PILImage
    img = PILImage.open(str(path))
    return [_as_gray_field(np.array(img))]


def channel_names(path: Path) -> list[str]:
    if path.suffix.lower() == ".npz":
        try:
            with np.load(str(path)) as npz:
                return sorted(npz.files)
        except Exception:
            pass
    return ["field"]
