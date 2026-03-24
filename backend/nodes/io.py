"""
I/O nodes: load and save images and SPM data.
"""

from __future__ import annotations
import os
import numpy as np
from pathlib import Path

from backend.node_registry import register_node
from backend.data_types import DataField, encode_preview, image_to_uint8
from backend.runtime_paths import demo_dir, input_dir, output_dir

# Resolved at server startup so nodes know where to look
DEMO_DIR = demo_dir()
INPUT_DIR = input_dir()
OUTPUT_DIR = output_dir()

_DEMO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".npy", ".npz",
                    ".gwy", ".sxm", ".ibw"}


# ---------------------------------------------------------------------------
# LoadImage
# ---------------------------------------------------------------------------

@register_node(display_name="Load Image")
class LoadImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("FILE_PICKER", {"default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE", "DATA_FIELD")
    RETURN_NAMES = ("image", "field")
    FUNCTION = "load"
    CATEGORY = "io"
    DESCRIPTION = "Load a PNG, TIFF, JPG image or .npy/.npz array from the input folder. Outputs both IMAGE and DATA_FIELD."

    def load(self, filename: str):
        # Accept absolute paths or filenames relative to input/
        path = Path(filename)
        if not path.is_absolute():
            path = INPUT_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        ext = path.suffix.lower()
        if ext in (".npy",):
            arr = np.load(str(path)).astype(np.float64)
        elif ext in (".npz",):
            npz = np.load(str(path))
            key = list(npz.files)[0]
            arr = npz[key].astype(np.float64)
        else:
            from PIL import Image
            img = Image.open(str(path))
            arr = np.array(img)
            if arr.dtype != np.uint8:
                arr = arr.astype(np.float64)

        # Convert to float64 grayscale for the DATA_FIELD output
        if arr.ndim == 3:
            gray = np.mean(arr.astype(np.float64), axis=2)
        else:
            gray = arr.astype(np.float64)

        field = DataField(data=gray)
        return (arr, field)


# ---------------------------------------------------------------------------
# LoadDemo
# ---------------------------------------------------------------------------

def _list_demo_files() -> list[str]:
    """Return sorted list of demo filenames available in the demo/ directory."""
    if not DEMO_DIR.exists():
        return []
    return sorted(
        f.name for f in DEMO_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in _DEMO_EXTENSIONS
    )


@register_node(display_name="Load Demo Image")
class LoadDemo:
    @classmethod
    def INPUT_TYPES(cls):
        choices = _list_demo_files() or ["(no demo images found)"]
        return {
            "required": {
                "name": (choices,),
            }
        }

    RETURN_TYPES = ("IMAGE", "DATA_FIELD")
    RETURN_NAMES = ("image", "field")
    FUNCTION = "load"
    CATEGORY = "io"
    DESCRIPTION = "Load a bundled demo image so you can try the app without providing your own data."

    def load(self, name: str):
        path = DEMO_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Demo image not found: {name}")

        ext = path.suffix.lower()

        # SPM formats → delegate to LoadSPM-style loading, return as IMAGE + DATA_FIELD
        if ext == ".gwy":
            field = LoadSPM()._load_gwy(path, "Z")
            arr = field.data
            return (arr, field)
        elif ext == ".sxm":
            field = LoadSPM()._load_sxm(path, "Z")
            arr = field.data
            return (arr, field)
        elif ext == ".ibw":
            field = LoadSPM()._load_ibw(path)
            arr = field.data
            return (arr, field)

        # npy / npz
        if ext == ".npy":
            arr = np.load(str(path)).astype(np.float64)
        elif ext == ".npz":
            npz = np.load(str(path))
            key = list(npz.files)[0]
            arr = npz[key].astype(np.float64)
        else:
            from PIL import Image
            img = Image.open(str(path))
            arr = np.array(img)
            if arr.dtype != np.uint8:
                arr = arr.astype(np.float64)

        if arr.ndim == 3:
            gray = np.mean(arr.astype(np.float64), axis=2)
        else:
            gray = arr.astype(np.float64)

        field = DataField(data=gray)
        return (arr, field)


# ---------------------------------------------------------------------------
# LoadSPM
# ---------------------------------------------------------------------------

@register_node(display_name="Load SPM File")
class LoadSPM:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "filename": ("FILE_PICKER", {"default": ""}),
                "channel": ("STRING", {"default": "Z"}),
            }
        }

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("field",)
    FUNCTION = "load"
    CATEGORY = "io"
    DESCRIPTION = "Load SPM/AFM data from .gwy, .sxm, or .ibw files into a calibrated DataField."

    def load(self, filename: str, channel: str = "Z"):
        path = Path(filename)
        if not path.is_absolute():
            path = INPUT_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        ext = path.suffix.lower()

        if ext == ".gwy":
            return (self._load_gwy(path, channel),)
        elif ext == ".sxm":
            return (self._load_sxm(path, channel),)
        elif ext in (".ibw",):
            return (self._load_ibw(path),)
        elif ext in (".npy",):
            data = np.load(str(path)).astype(np.float64)
            return (DataField(data=data),)
        elif ext in (".npz",):
            npz = np.load(str(path))
            key = list(npz.files)[0]
            return (DataField(data=npz[key].astype(np.float64)),)
        else:
            raise ValueError(f"Unsupported SPM format: {ext}. Supported: .gwy, .sxm, .ibw, .npy, .npz")

    def _load_gwy(self, path: Path, channel: str) -> DataField:
        try:
            import gwyfile
        except ImportError:
            raise ImportError("Install 'gwyfile' package to load .gwy files: pip install gwyfile")

        obj = gwyfile.load(str(path))
        channels = gwyfile.util.get_datafields(obj)
        if not channels:
            raise ValueError(f"No data channels found in {path.name}")

        # Try requested channel name, fall back to first available
        ch = None
        for key, df in channels.items():
            if channel.lower() in key.lower():
                ch = df
                break
        if ch is None:
            ch = next(iter(channels.values()))

        data = np.array(ch.data, dtype=np.float64).reshape(ch.yres, ch.xres)
        return DataField(
            data=data,
            xreal=float(ch.xreal),
            yreal=float(ch.yreal),
            xoff=float(getattr(ch, "xoff", 0.0)),
            yoff=float(getattr(ch, "yoff", 0.0)),
            si_unit_xy="m",
            si_unit_z="m",
        )

    def _load_sxm(self, path: Path, channel: str) -> DataField:
        try:
            import nanonispy as nap
        except ImportError:
            raise ImportError("Install 'nanonispy' package to load .sxm files: pip install nanonispy")

        sxm = nap.read.Scan(str(path))
        signals = sxm.signals

        # Pick channel
        ch_key = None
        for key in signals:
            if channel.upper() in key.upper():
                ch_key = key
                break
        if ch_key is None:
            ch_key = next(iter(signals))

        data = signals[ch_key].get("forward", list(signals[ch_key].values())[0])
        data = np.asarray(data, dtype=np.float64)
        if data.ndim != 2:
            data = data.reshape(data.shape[-2], data.shape[-1])

        header = sxm.header
        scan_range = header.get("scan_range", [1e-6, 1e-6])
        return DataField(
            data=data,
            xreal=float(scan_range[0]),
            yreal=float(scan_range[1]),
            si_unit_xy="m",
            si_unit_z="m",
        )

    def _load_ibw(self, path: Path) -> DataField:
        try:
            import igor.igorpy as igorpy
            wave = igorpy.load(str(path))
            data = wave.wave["wData"].squeeze().astype(np.float64)
        except ImportError:
            raise ImportError("Install 'igor' package to load .ibw files: pip install igor")

        if data.ndim == 1:
            data = data.reshape(1, -1)
        elif data.ndim != 2:
            data = data[:, :, 0] if data.ndim == 3 else data.reshape(data.shape[0], -1)

        return DataField(data=data, si_unit_xy="m", si_unit_z="m")


# ---------------------------------------------------------------------------
# Coordinate
# ---------------------------------------------------------------------------

@register_node(display_name="Coordinate")
class Coordinate:
    """Provide a fractional (x, y) point for use with Cross Section or other nodes."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "x": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "y": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("COORD",)
    RETURN_NAMES = ("point",)
    FUNCTION = "process"
    CATEGORY = "io"
    DESCRIPTION = "Output a fractional (x, y) coordinate pair in [0, 1]."

    def process(self, x: float, y: float) -> tuple:
        return ((float(x), float(y)),)


# ---------------------------------------------------------------------------
# SaveImage
# ---------------------------------------------------------------------------

@register_node(display_name="Save Image")
class SaveImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "output"}),
                "format": (["PNG", "TIFF", "NPY"],),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save"
    CATEGORY = "io"
    OUTPUT_NODE = True
    DESCRIPTION = "Save an image or array to the output folder."

    # Injected by server.py before execution begins
    _broadcast_preview = None

    def save(self, image: np.ndarray, filename_prefix: str = "output", format: str = "PNG"):
        OUTPUT_DIR.mkdir(exist_ok=True)

        # Find next available filename
        idx = 1
        while True:
            name = f"{filename_prefix}_{idx:04d}"
            candidate = OUTPUT_DIR / f"{name}.{format.lower()}"
            if not candidate.exists():
                break
            idx += 1

        if format == "NPY":
            np.save(str(OUTPUT_DIR / f"{name}.npy"), image)
        else:
            from PIL import Image
            arr = image_to_uint8(image)
            if arr.ndim == 2:
                pil_img = Image.fromarray(arr, mode="L")
            else:
                pil_img = Image.fromarray(arr, mode="RGB")
            pil_img.save(str(OUTPUT_DIR / f"{name}.{format.lower()}"))

        # Emit preview over WebSocket if callback is set
        if SaveImage._broadcast_preview is not None:
            arr_u8 = image_to_uint8(image)
            data_uri = encode_preview(arr_u8)
            SaveImage._broadcast_preview(data_uri)

        return ()
