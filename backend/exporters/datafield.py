"""
Exporter for DATA_FIELD values (single layer or multi-layer stacks).

Format choices:

* **TIFF** — 8-bit RGB colormap preview. *Not* round-trippable and single-layer
  only; connect multiple channels and pick "TIFF (data)" for a stack.
* **TIFF (data)** — float64 pixels with tono metadata JSON-embedded in the
  TIFF ImageDescription tag. Round-trips and supports multi-page stacks: one
  IFD per layer, the first page's description carries a ``{"tono": {...},
  "layers": [...]}`` document.
* **PNG** — 8-bit RGB colormap preview. Single-layer only.
* **NPZ** — for a single layer, writes a plain ``field=...`` key. For a stack,
  each layer gets its own key derived from its display name (identifier-safe,
  deduplicated).
* **GWY** — Gwyddion native format via the ``gwyfile`` package. A multi-layer
  save writes one channel per layer (``/0/data``, ``/1/data``, …), each with
  its own title, producing a true multi-channel .gwy file.
* **HDF5** — generic HDF5 with one ``data`` dataset per layer and physical
  dimensions as dataset attrs. Round-trips via the HDF5 importer (plain
  datasets without the Ergo sidecar group), which picks up every 2-D numeric
  dataset.
* **HDF5 (Ergo)** — Asylum Research / Ergo layout, one dataset per layer under
  ``Image/DataSet/Resolution 0/Frame 0/<title>/Image`` plus a matching sidecar
  group ``Image/DataSetInfo/Global/Channels/<title>/ImageDims``. Round-trips
  via the Ergo layout importer and opens in Ergo / Igor.

Mixed layer stacks (DataField + Image) are supported for TIFF (data) and NPZ
only; the physics-carrying formats (GWY, HDF5, HDF5 Ergo) require every layer
to be a DataField and raise a clear error otherwise.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from backend.data_types import DataField, datafield_to_uint8, image_to_uint8
from backend.exporters._base import FormatSpec

accepted_types: tuple[str, ...] = ("DATA_FIELD",)

FORMATS: dict[str, FormatSpec] = {
    "TIFF":        FormatSpec(ext=".tiff", round_trip=False, label="TIFF (preview)"),
    "TIFF (data)": FormatSpec(ext=".tiff", round_trip=True,  label="TIFF (calibrated data)"),
    "PNG":         FormatSpec(ext=".png",  round_trip=False, label="PNG (preview)"),
    "NPZ":         FormatSpec(ext=".npz",  round_trip=False, label="NumPy (.npz)"),
    "GWY":         FormatSpec(ext=".gwy",  round_trip=True,  label="Gwyddion (.gwy)"),
    "HDF5":        FormatSpec(ext=".h5",   round_trip=True,  label="HDF5 (generic)"),
    "HDF5 (Ergo)": FormatSpec(ext=".h5",   round_trip=True,  label="HDF5 (Asylum Research / Ergo)"),
}

# Formats that only make sense for a single layer. When extra layers are
# connected, the Save node raises before we get here, but we keep the check
# defensive so the protocol is enforced at the exporter boundary too.
_SINGLE_LAYER_ONLY: frozenset[str] = frozenset({"TIFF", "PNG"})


def save(
    path: Path,
    value: DataField,
    format_name: str,
    *,
    extra_layers: Sequence[Any] | None = None,
    layer_names: Sequence[str] | None = None,
    **_opts,
) -> None:
    extras = list(extra_layers or [])
    layers: list[Any] = [value, *extras]
    names = _resolve_layer_names(layers, layer_names, default_primary=path.stem or "field")

    if extras and format_name in _SINGLE_LAYER_ONLY:
        raise ValueError(
            f"{format_name} only supports a single layer. Use 'TIFF (data)', "
            f"'NPZ', 'GWY', or an HDF5 format for multi-layer saves."
        )

    if format_name == "TIFF":
        _save_tiff_preview(path, value)
        return
    if format_name == "TIFF (data)":
        _save_tiff_data(path, layers, names)
        return
    if format_name == "PNG":
        _save_png_preview(path, value)
        return
    if format_name == "NPZ":
        _save_npz(path, layers, names)
        return
    if format_name == "GWY":
        _save_gwy(path, _require_all_datafields(layers, "GWY"), names)
        return
    if format_name == "HDF5":
        _save_hdf5_generic(path, _require_all_datafields(layers, "HDF5"), names)
        return
    if format_name == "HDF5 (Ergo)":
        _save_hdf5_ergo(path, _require_all_datafields(layers, "HDF5 (Ergo)"), names)
        return
    raise ValueError(f"Format {format_name!r} is not supported for DATA_FIELD.")


# ---------------------------------------------------------------------------
# Layer helpers
# ---------------------------------------------------------------------------


def _resolve_layer_names(
    layers: Sequence[Any],
    raw_names: Sequence[str] | None,
    *,
    default_primary: str,
) -> list[str]:
    """Fill in layer names, falling back to defaults for blank/missing entries.

    The primary layer (index 0) defaults to ``default_primary`` (usually the
    file stem), and each extra layer defaults to ``layer_N+1`` (1-indexed for
    humans: "layer 2", "layer 3", …).
    """
    raw_names = list(raw_names or [])
    out: list[str] = []
    for i in range(len(layers)):
        raw = str(raw_names[i]).strip() if i < len(raw_names) and raw_names[i] is not None else ""
        if raw:
            out.append(raw)
        elif i == 0:
            out.append(default_primary)
        else:
            out.append(f"layer_{i + 1}")
    return out


def _require_all_datafields(layers: Sequence[Any], format_label: str) -> list[DataField]:
    """Return the list cast to DataFields, raising if any layer is not one."""
    out: list[DataField] = []
    for i, layer in enumerate(layers):
        if not isinstance(layer, DataField):
            raise ValueError(
                f"{format_label} only supports DataField layers; layer {i + 1} "
                f"is a {type(layer).__name__}. Use TIFF (data) or NPZ for mixed stacks."
            )
        out.append(layer)
    return out


def _safe_identifier(name: str, index: int) -> str:
    """Turn a free-form layer name into a safe identifier (used as an NPZ key)."""
    key = re.sub(r"[^0-9A-Za-z_]+", "_", str(name).strip()).strip("_")
    if not key:
        key = f"layer_{index + 1}"
    if key[0].isdigit():
        key = f"layer_{key}"
    return key


def _dedupe_keys(raw_keys: Sequence[str]) -> list[str]:
    used: set[str] = set()
    result: list[str] = []
    for k in raw_keys:
        candidate = k
        suffix = 2
        while candidate in used:
            candidate = f"{k}_{suffix}"
            suffix += 1
        used.add(candidate)
        result.append(candidate)
    return result


def _layer_to_float_array(layer: Any) -> np.ndarray:
    """Coerce a layer into a float array for TIFF (data). Images are promoted."""
    if isinstance(layer, DataField):
        return np.ascontiguousarray(layer.data, dtype=np.float64)
    if isinstance(layer, np.ndarray):
        # Images are left as-is so multi-channel RGB pages survive the write.
        return np.ascontiguousarray(layer)
    raise ValueError(f"Unsupported layer type for TIFF (data): {type(layer).__name__}")


def _layer_to_npz_array(layer: Any) -> np.ndarray:
    if isinstance(layer, DataField):
        return np.asarray(layer.data)
    if isinstance(layer, np.ndarray):
        return np.asarray(layer)
    raise ValueError(f"Unsupported layer type for NPZ: {type(layer).__name__}")


def _datafield_meta(field: DataField) -> dict:
    """Build the JSON-serializable physics metadata dict for a DataField."""
    return {
        "xreal": float(field.xreal),
        "yreal": float(field.yreal),
        "xoff": float(field.xoff),
        "yoff": float(field.yoff),
        "si_unit_xy": str(field.si_unit_xy),
        "si_unit_z": str(field.si_unit_z),
        "domain": str(field.domain),
        "colormap": field.colormap if isinstance(field.colormap, str) else "viridis",
    }


# ---------------------------------------------------------------------------
# Per-format writers
# ---------------------------------------------------------------------------


def _save_tiff_preview(path: Path, field: DataField) -> None:
    import tifffile
    tifffile.imwrite(str(path), datafield_to_uint8(field, field.colormap))


def _save_tiff_data(path: Path, layers: Sequence[Any], names: Sequence[str]) -> None:
    """Write the raw pixels as a multi-page TIFF with tono metadata.

    The ImageDescription tag on the first page carries a JSON document of
    shape ``{"tono": {"version": 1, "layers": [{...}, {...}]}}``. Each entry in
    ``layers`` gives the per-layer physics (xreal/yreal/xoff/yoff/units/domain)
    and its display name so a future multi-layer importer can reconstruct the
    whole stack. Non-DataField layers (plain images) get a minimal entry with
    just the name and dtype — they're pixels, not physics.
    """
    import tifffile

    per_layer_meta: list[dict] = []
    for layer, layer_name in zip(layers, names):
        if isinstance(layer, DataField):
            entry = {"name": layer_name, "kind": "data_field", **_datafield_meta(layer)}
        else:
            arr = np.asarray(layer)
            entry = {"name": layer_name, "kind": "image", "dtype": str(arr.dtype), "shape": list(arr.shape)}
        per_layer_meta.append(entry)

    description = json.dumps(
        {"tono": {"version": 1, "layers": per_layer_meta}},
        separators=(",", ":"),
    )

    with tifffile.TiffWriter(str(path)) as tif:
        for i, (layer, layer_name) in enumerate(zip(layers, names)):
            arr = _layer_to_float_array(layer)
            # Full metadata document lives on the first page; subsequent pages
            # carry only their display name so readers that walk IFDs see
            # something meaningful per channel.
            page_desc = description if i == 0 else layer_name
            tif.write(arr, description=page_desc)


def _save_png_preview(path: Path, field: DataField) -> None:
    from PIL import Image
    Image.fromarray(datafield_to_uint8(field, field.colormap)).save(str(path))


def _save_npz(path: Path, layers: Sequence[Any], names: Sequence[str]) -> None:
    if len(layers) == 1:
        # Single-layer: keep the historical `field` key so nothing that reads
        # existing tono .npz outputs breaks.
        np.savez(str(path), field=_layer_to_npz_array(layers[0]))
        return
    raw_keys = [_safe_identifier(name, i) for i, name in enumerate(names)]
    keys = _dedupe_keys(raw_keys)
    arrays = {key: _layer_to_npz_array(layer) for key, layer in zip(keys, layers)}
    np.savez(str(path), **arrays)


def _save_gwy(path: Path, fields: list[DataField], names: Sequence[str]) -> None:
    """Write an N-channel .gwy file via the gwyfile package."""
    from gwyfile.objects import GwyContainer, GwyDataField, GwySIUnit

    container_data: dict[str, Any] = {}
    for i, (field, title) in enumerate(zip(fields, names)):
        gwy_field = GwyDataField(
            np.ascontiguousarray(field.data, dtype=np.float64),
            xreal=float(field.xreal),
            yreal=float(field.yreal),
            xoff=float(field.xoff),
            yoff=float(field.yoff),
            si_unit_xy=GwySIUnit(unitstr=str(field.si_unit_xy or "")),
            si_unit_z=GwySIUnit(unitstr=str(field.si_unit_z or "")),
        )
        container_data[f"/{i}/data"] = gwy_field
        container_data[f"/{i}/data/title"] = title
    GwyContainer(container_data).tofile(str(path))


def _save_hdf5_generic(path: Path, fields: list[DataField], names: Sequence[str]) -> None:
    """Write one HDF5 dataset per layer with physical dims as dataset attrs.

    Single-layer saves use ``/data`` for backward compatibility with the
    tests that read the original layout; multi-layer saves use one
    top-level dataset per channel, keyed by the safe-identifier form of its
    name and deduplicated against collisions.
    """
    import h5py

    with h5py.File(str(path), "w") as f:
        if len(fields) == 1:
            _write_hdf5_dataset(f, "data", fields[0])
            return
        raw_keys = [_safe_identifier(name, i) for i, name in enumerate(names)]
        keys = _dedupe_keys(raw_keys)
        for key, field in zip(keys, fields):
            _write_hdf5_dataset(f, key, field)


def _write_hdf5_dataset(h5file: Any, name: str, field: DataField) -> None:
    arr = np.ascontiguousarray(field.data, dtype=np.float64)
    ds = h5file.create_dataset(name, data=arr)
    ds.attrs["xreal"] = float(field.xreal)
    ds.attrs["yreal"] = float(field.yreal)
    ds.attrs["xoff"]  = float(field.xoff)
    ds.attrs["yoff"]  = float(field.yoff)
    ds.attrs["si_unit_xy"] = str(field.si_unit_xy or "")
    ds.attrs["si_unit_z"]  = str(field.si_unit_z or "")


def _save_hdf5_ergo(path: Path, fields: list[DataField], names: Sequence[str]) -> None:
    """Write an Asylum Research / Ergo-compatible HDF5 file (N channels).

    Each channel gets its own dataset at
    ``Image/DataSet/Resolution 0/Frame 0/<title>/Image`` with a matching
    sidecar group ``Image/DataSetInfo/Global/Channels/<title>/ImageDims``
    carrying ``DimScaling`` / ``DimUnits`` / ``DataUnits``. The channel
    names are the dedupe-safe form of each layer name. Opens in Ergo / Igor
    and round-trips through :mod:`backend.importers.ergo_hdf5`.
    """
    import h5py

    raw_keys = [_safe_identifier(name, i) for i, name in enumerate(names)]
    titles = _dedupe_keys(raw_keys)

    with h5py.File(str(path), "w") as f:
        for field, title in zip(fields, titles):
            arr = np.ascontiguousarray(field.data, dtype=np.float64)
            ds = f.create_dataset(
                f"Image/DataSet/Resolution 0/Frame 0/{title}/Image",
                data=arr,
            )
            ds.attrs["xreal"] = float(field.xreal)
            ds.attrs["yreal"] = float(field.yreal)
            ds.attrs["xoff"]  = float(field.xoff)
            ds.attrs["yoff"]  = float(field.yoff)
            xy_unit = str(field.si_unit_xy or "m")
            z_unit  = str(field.si_unit_z or "")
            ds.attrs["si_unit_xy"] = xy_unit
            ds.attrs["si_unit_z"]  = z_unit

            x_start = float(field.xoff)
            x_end   = float(field.xoff) + float(field.xreal)
            y_start = float(field.yoff)
            y_end   = float(field.yoff) + float(field.yreal)
            # DimScaling is Y-first to match the importer (ergo_hdf5.py:110-113).
            dim_scaling = np.array(
                [[y_start, y_end], [x_start, x_end]],
                dtype=np.float64,
            )
            dim_units = np.array([xy_unit, xy_unit], dtype=h5py.string_dtype())

            dims_grp = f.create_group(
                f"Image/DataSetInfo/Global/Channels/{title}/ImageDims"
            )
            dims_grp.attrs["DimScaling"] = dim_scaling
            dims_grp.attrs["DimUnits"]   = dim_units
            dims_grp.attrs["DataUnits"]  = z_unit
