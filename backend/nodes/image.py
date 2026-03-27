from __future__ import annotations
import numpy as np
from pathlib import Path

from backend.node_registry import register_node
from backend.data_types import COLORMAPS, DataField, resolve_colormap_input
from backend.nodes.helpers import _resolve_path, _SPM_EXTENSIONS


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

    RETURN_TYPES = ("DATA_FIELD",)
    RETURN_NAMES = ("field",)
    FUNCTION = "load"

    DESCRIPTION = (
        "Load any supported file. "
        "SPM formats (.gwy, .sxm, .ibw) provide calibrated dimensions; "
        "each channel gets its own output. "
        "Images (.png, .tiff, .jpg) and arrays (.npy, .npz) are loaded as uncalibrated fields."
    )

    _broadcast_warning_fn = None
    _current_node_id = None

    def load(self, filename: str = "", colormap: str = "viridis", colormap_map=None, path: str | None = None):
        selected_path = str(path).strip() if path is not None else str(filename).strip()
        if not selected_path:
            raise ValueError("No file selected — use Browse to pick a file.")
        path_obj = _resolve_path(selected_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path_obj}")
        if path_obj.is_dir():
            raise IsADirectoryError(f"Expected a file, got a directory: {path_obj}")

        ext = path_obj.suffix.lower()
        resolved_colormap = resolve_colormap_input(colormap, colormap_input=colormap_map, default="viridis")

        if ext in _SPM_EXTENSIONS:
            fields = self._load_spm_all(path_obj, ext)
            for f in fields:
                f.colormap = resolved_colormap
            return tuple(fields)

        field = self._load_image_or_array(path_obj, ext)
        field.colormap = resolved_colormap
        self._send_warning("Uncalibrated data — no physical dimensions.")
        return (field,)

    def _send_warning(self, message: str):
        fn = Image._broadcast_warning_fn
        nid = Image._current_node_id
        if fn and nid:
            fn(nid, message)

    def _load_spm_all(self, path: Path, ext: str) -> list[DataField]:
        if ext == ".gwy":
            return self._load_gwy_all(path)
        elif ext == ".sxm":
            return self._load_sxm_all(path)
        elif ext == ".ibw":
            return self._load_ibw_all(path)
        else:
            raise ValueError(f"Unsupported SPM format: {ext}")

    def _load_gwy_all(self, path: Path) -> list[DataField]:
        try:
            import gwyfile
        except ImportError:
            raise ImportError("Install 'gwyfile' package to load .gwy files: pip install gwyfile")

        obj = gwyfile.load(str(path))
        channels = gwyfile.util.get_datafields(obj)
        if not channels:
            raise ValueError(f"No data channels found in {path.name}")

        fields = []
        for ch in channels.values():
            data = np.array(ch.data, dtype=np.float64).reshape(ch.yres, ch.xres)
            fields.append(DataField(
                data=data,
                xreal=float(ch.xreal),
                yreal=float(ch.yreal),
                xoff=float(getattr(ch, "xoff", 0.0)),
                yoff=float(getattr(ch, "yoff", 0.0)),
                si_unit_xy="m",
                si_unit_z="m",
            ))
        return fields

    def _load_sxm_all(self, path: Path) -> list[DataField]:
        try:
            import nanonispy as nap
        except ImportError:
            raise ImportError("Install 'nanonispy' package to load .sxm files: pip install nanonispy")

        sxm = nap.read.Scan(str(path))
        signals = sxm.signals
        if not signals:
            raise ValueError(f"No signals found in {path.name}")

        header = sxm.header
        scan_range = header.get("scan_range", [1e-6, 1e-6])

        fields = []
        for sig in signals.values():
            data = sig.get("forward", list(sig.values())[0])
            data = np.asarray(data, dtype=np.float64)
            if data.ndim != 2:
                data = data.reshape(data.shape[-2], data.shape[-1])
            fields.append(DataField(
                data=data,
                xreal=float(scan_range[0]),
                yreal=float(scan_range[1]),
                si_unit_xy="m",
                si_unit_z="m",
            ))
        return fields

    def _load_ibw_all(self, path: Path) -> list[DataField]:
        try:
            from igor.binarywave import load as load_ibw
        except ImportError:
            raise ImportError("Install 'igor' package to load .ibw files: pip install igor")

        wave = load_ibw(str(path))
        wdata = wave["wave"]
        header = wdata["wave_header"]
        raw = wdata["wData"]

        n_channels = raw.shape[2] if raw.ndim >= 3 else 1

        sfA = header.get("sfA", None)

        def _decode_unit(raw_unit):
            if raw_unit is None:
                return "m"
            if isinstance(raw_unit, bytes):
                return raw_unit.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip() or "m"
            if isinstance(raw_unit, np.ndarray):
                return bytes(raw_unit).split(b"\x00", 1)[0].decode("ascii", errors="replace").strip() or "m"
            return str(raw_unit).strip() or "m"

        dim_units_raw = header.get("dimUnits", None)
        data_units_raw = header.get("dataUnits", None)

        if isinstance(dim_units_raw, np.ndarray) and dim_units_raw.ndim == 2:
            si_unit_xy = _decode_unit(dim_units_raw[0])
        elif isinstance(dim_units_raw, (list, np.ndarray)) and len(dim_units_raw) > 0:
            si_unit_xy = _decode_unit(dim_units_raw[0])
        else:
            si_unit_xy = _decode_unit(dim_units_raw)

        si_unit_z = _decode_unit(data_units_raw)

        fields = []
        for ch_idx in range(n_channels):
            if raw.ndim >= 3:
                ch_data = raw[:, :, ch_idx]
            elif raw.ndim == 1:
                ch_data = raw.reshape(-1, 1)
            else:
                ch_data = raw

            data = np.flipud(ch_data.T).astype(np.float64)
            yres, xres = data.shape

            if sfA is not None and len(sfA) >= 2:
                xreal = abs(float(sfA[0]) * xres) or 1e-6
                yreal = abs(float(sfA[1]) * yres) or 1e-6
            else:
                hsA = header.get("hsA", 0.0)
                xreal = abs(float(hsA) * xres) or 1e-6
                yreal = xreal * (yres / xres) if xres else 1e-6

            fields.append(DataField(
                data=data, xreal=xreal, yreal=yreal,
                si_unit_xy=si_unit_xy, si_unit_z=si_unit_z,
            ))

        return fields

    def _load_image_or_array(self, path: Path, ext: str) -> DataField:
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

        return DataField(data=gray)
