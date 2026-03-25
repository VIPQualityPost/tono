"""
Core data types for argonode.

DataField mirrors Gwyddion's GwyDataField structure:
  xres, yres  – pixel dimensions
  xreal, yreal – physical dimensions in metres
  xoff, yoff   – position offset in metres
  si_unit_xy   – lateral unit string (e.g. "m", "nm")
  si_unit_z    – height/value unit string (e.g. "m", "V", "A")
  domain       – "spatial" or "frequency" (set by FFT nodes)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np


COLORMAPS = ("viridis", "gray", "hot", "jet", "plasma", "inferno", "terrain",
             "cividis", "magma", "copper", "afmhot")


class RecordTable(list):
    """Tabular rows with a shared schema, e.g. particle statistics."""


class MeasureTable(list):
    """Named scalar measurements, typically rows of quantity/value/unit."""

@dataclass
class DataField:
    data: np.ndarray        # shape (yres, xres), dtype float64
    xres: int = 0
    yres: int = 0
    xreal: float = 1e-6    # physical width in metres
    yreal: float = 1e-6    # physical height in metres
    xoff: float = 0.0
    yoff: float = 0.0
    si_unit_xy: str = "m"
    si_unit_z: str = "m"
    domain: str = "spatial"  # "spatial" or "frequency"
    colormap: str = "viridis"
    display_offset: float = 0.0
    display_scale: float = 1.0

    def __post_init__(self) -> None:
        self.data = np.asarray(self.data, dtype=np.float64)
        if self.data.ndim != 2:
            raise ValueError(f"DataField.data must be 2-D, got shape {self.data.shape}")
        self.yres, self.xres = self.data.shape

    def copy(self) -> "DataField":
        """Return a deep copy with independent data array."""
        return DataField(
            data=self.data.copy(),
            xres=self.xres,
            yres=self.yres,
            xreal=self.xreal,
            yreal=self.yreal,
            xoff=self.xoff,
            yoff=self.yoff,
            si_unit_xy=self.si_unit_xy,
            si_unit_z=self.si_unit_z,
            domain=self.domain,
            colormap=self.colormap,
            display_offset=self.display_offset,
            display_scale=self.display_scale,
        )

    def replace(self, **kwargs) -> "DataField":
        """Return a copy with selected fields replaced. data is deep-copied unless provided."""
        base = {
            "data": self.data.copy(),
            "xres": self.xres,
            "yres": self.yres,
            "xreal": self.xreal,
            "yreal": self.yreal,
            "xoff": self.xoff,
            "yoff": self.yoff,
            "si_unit_xy": self.si_unit_xy,
            "si_unit_z": self.si_unit_z,
            "domain": self.domain,
            "colormap": self.colormap,
            "display_offset": self.display_offset,
            "display_scale": self.display_scale,
        }
        base.update(kwargs)
        return DataField(**base)

    @property
    def dx(self) -> float:
        """Physical pixel size in x (metres)."""
        return self.xreal / self.xres if self.xres else 1.0

    @property
    def dy(self) -> float:
        """Physical pixel size in y (metres)."""
        return self.yreal / self.yres if self.yres else 1.0


# ---------------------------------------------------------------------------
# Utility helpers shared across nodes
# ---------------------------------------------------------------------------

def normalize_for_colormap(
    data: np.ndarray,
    *,
    offset: float = 0.0,
    scale: float = 1.0,
    data_min: float | None = None,
    data_max: float | None = None,
) -> np.ndarray:
    """
    Normalize an array to [0, 1] for colormap lookup, then apply a display window.

    offset/scale operate in normalized data coordinates:
      output = clip((base_norm - offset) / scale, 0, 1)
    So offset=0, scale=1 maps the full data range 1:1 into the colormap.
    """
    data = np.asarray(data, dtype=np.float64)
    dmin = float(data.min()) if data_min is None else float(data_min)
    dmax = float(data.max()) if data_max is None else float(data_max)

    if dmax > dmin:
        base_norm = (data - dmin) / (dmax - dmin)
    else:
        base_norm = np.zeros_like(data)

    offset = float(offset)
    scale = float(scale)
    if not np.isfinite(offset):
        offset = 0.0
    if not np.isfinite(scale) or scale <= 0.0:
        scale = 1.0

    return np.clip((base_norm - offset) / scale, 0.0, 1.0)


def datafield_to_uint8(df: DataField, colormap: str = "gray") -> np.ndarray:
    """
    Normalize a DataField to a uint8 (H, W, 3) RGB array using matplotlib colormap.
    Returns shape (H, W, 3) uint8.
    """
    import matplotlib.cm as cm
    normalized = normalize_for_colormap(
        df.data,
        offset=df.display_offset,
        scale=df.display_scale,
    )

    cmap = cm.get_cmap(colormap)
    rgba = cmap(normalized)                     # (H, W, 4) float [0,1]
    rgb = (rgba[:, :, :3] * 255).astype(np.uint8)
    return rgb


def image_to_uint8(image: np.ndarray) -> np.ndarray:
    """
    Convert an IMAGE (float or uint8, 2-D or 3-D) to uint8 (H,W,3) or (H,W) for PIL.
    """
    if image.dtype == np.uint8:
        return image
    # float — normalize to [0, 255]
    imin, imax = image.min(), image.max()
    if imax > imin:
        out = (image - imin) / (imax - imin) * 255.0
    else:
        out = np.zeros_like(image)
    return out.astype(np.uint8)


def encode_preview(arr: np.ndarray) -> str:
    """
    Encode a uint8 numpy array as a base64 data URI (PNG).
    arr: (H, W) grayscale or (H, W, 3) RGB, uint8.
    """
    import base64
    import io
    from PIL import Image

    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"
