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


def _load_tono_tiff(path: Path) -> list[DataField] | None:
    """Read a tono 'TIFF (data)' export back into calibrated DataFields.

    The exporter stores float64 pages plus a ``{"tono": {"version": 1,
    "layers": [...]}}`` ImageDescription on the first page. Returns None for
    any TIFF without that marker so plain images keep the pixel-only path.
    """
    import json

    import tifffile

    from backend.data_types import COLORMAPS, DataField

    try:
        with tifffile.TiffFile(str(path)) as tif:
            if not tif.pages:
                return None
            desc = tif.pages[0].tags.get("ImageDescription")
            if desc is None:
                return None
            try:
                doc = json.loads(desc.value)
            except (ValueError, TypeError):
                return None
            meta = doc.get("tono") if isinstance(doc, dict) else None
            if not isinstance(meta, dict):
                return None
            layers: list[dict] = meta.get("layers") or []

            fields = []
            for i, page in enumerate(tif.pages):
                arr = np.asarray(page.asarray(), dtype=np.float64)
                entry = layers[i] if i < len(layers) else {}
                if entry.get("kind") == "data_field" and arr.ndim == 2:
                    colormap = str(entry.get("colormap", "") or "")
                    if colormap not in COLORMAPS:
                        colormap = "viridis"
                    try:
                        fields.append(DataField(
                            data=arr,
                            xreal=float(entry.get("xreal", 1e-6)),
                            yreal=float(entry.get("yreal", 1e-6)),
                            xoff=float(entry.get("xoff", 0.0)),
                            yoff=float(entry.get("yoff", 0.0)),
                            si_unit_xy=str(entry.get("si_unit_xy", "m")),
                            si_unit_z=str(entry.get("si_unit_z", "m")),
                            domain=str(entry.get("domain", "spatial")),
                            colormap=colormap,
                        ))
                        continue
                    except Exception:
                        pass
                fields.append(_as_gray_field(arr))
            return fields
    except Exception:
        return None


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

    if ext in (".tiff", ".tif"):
        tono_fields = _load_tono_tiff(path)
        if tono_fields is not None:
            return tono_fields

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
