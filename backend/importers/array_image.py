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


def load(path: Path) -> list[DataField]:
    ext = path.suffix.lower()

    if ext == ".npy":
        arr = np.load(str(path)).astype(np.float64)
    elif ext == ".npz":
        npz = np.load(str(path))
        key = list(npz.files)[0]
        arr = npz[key].astype(np.float64)
    else:
        from PIL import Image as PILImage
        img = PILImage.open(str(path))
        arr = np.array(img)
        if arr.dtype != np.uint8:
            arr = arr.astype(np.float64)

    if arr.ndim == 3:
        gray = np.mean(arr.astype(np.float64), axis=2)
    else:
        gray = arr.astype(np.float64)

    return [DataField(data=gray)]


def channel_names(path: Path) -> list[str]:
    return ["field"]
