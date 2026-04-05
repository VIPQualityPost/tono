"""
Exporter for DATA_FIELD values.

Format choices:

* **TIFF** — 8-bit RGB colormap preview. *Not* round-trippable. Useful for
  figures and sharing; opening it back gives you pixels, not physics.
* **TIFF (data)** — float64 array with tono metadata JSON-embedded in the
  TIFF ImageDescription tag. Round-trips via the array_image importer once
  that importer learns to read the tag (see tests/node_tests/exporters.py).
* **PNG** — 8-bit RGB colormap preview. Not round-trippable.
* **NPZ** — raw ``data`` array only. Not round-trippable (units are dropped).
* **GWY** — Gwyddion native format via the ``gwyfile`` package. Round-trips
  and opens directly in Gwyddion. Recommended for "save and come back later".
* **HDF5** — generic HDF5 with one ``/data`` dataset and physical dimensions
  as dataset attrs. Round-trips via our generic ``hdf5`` importer.
* **HDF5 (Ergo)** — Asylum Research / Ergo layout with the dataset at
  ``Image/DataSet/Resolution 0/Frame 0/<title>/Image`` and a sidecar group
  ``Image/DataSetInfo/Global/Channels/<title>/ImageDims`` carrying
  ``DimScaling`` / ``DimUnits`` / ``DataUnits``. Round-trips via our
  ``ergo_hdf5`` importer and opens in Asylum Ergo / Igor.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from backend.data_types import DataField, datafield_to_uint8
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


def save(path: Path, value: DataField, format_name: str, **_opts) -> None:
    if format_name == "TIFF":
        _save_tiff_preview(path, value)
        return
    if format_name == "TIFF (data)":
        _save_tiff_data(path, value)
        return
    if format_name == "PNG":
        _save_png_preview(path, value)
        return
    if format_name == "NPZ":
        _save_npz(path, value)
        return
    if format_name == "GWY":
        _save_gwy(path, value)
        return
    if format_name == "HDF5":
        _save_hdf5_generic(path, value)
        return
    if format_name == "HDF5 (Ergo)":
        _save_hdf5_ergo(path, value)
        return
    raise ValueError(f"Format {format_name!r} is not supported for DATA_FIELD.")


def _save_tiff_preview(path: Path, field: DataField) -> None:
    import tifffile
    tifffile.imwrite(str(path), datafield_to_uint8(field, field.colormap))


def _save_tiff_data(path: Path, field: DataField) -> None:
    """Write the raw float64 data with tono metadata in the ImageDescription tag.

    The description is a JSON document of shape ``{"tono": {...}}`` so future
    schema extensions can coexist with other tools' TIFF metadata. Only the
    fields needed to reconstruct physical coordinates and z-scaling are
    embedded; display state (colormap, display_scale) is intentionally out of
    scope — this format is for data, not styling.
    """
    import tifffile

    meta = {
        "tono": {
            "version": 1,
            "xreal": float(field.xreal),
            "yreal": float(field.yreal),
            "xoff": float(field.xoff),
            "yoff": float(field.yoff),
            "si_unit_xy": str(field.si_unit_xy),
            "si_unit_z": str(field.si_unit_z),
            "domain": str(field.domain),
            "colormap": field.colormap if isinstance(field.colormap, str) else "viridis",
        }
    }
    tifffile.imwrite(
        str(path),
        np.ascontiguousarray(field.data, dtype=np.float64),
        description=json.dumps(meta, separators=(",", ":")),
    )


def _save_png_preview(path: Path, field: DataField) -> None:
    from PIL import Image
    Image.fromarray(datafield_to_uint8(field, field.colormap)).save(str(path))


def _save_npz(path: Path, field: DataField) -> None:
    np.savez(str(path), field=np.asarray(field.data))


def _save_gwy(path: Path, field: DataField) -> None:
    """Write a single-channel .gwy file via the gwyfile package."""
    from gwyfile.objects import GwyContainer, GwyDataField, GwySIUnit

    # gwyfile's GwyDataField ctor expects the data array and physical extents.
    # si_unit_xy / si_unit_z accept a GwySIUnit wrapper with a .unitstr field.
    gwy_field = GwyDataField(
        np.ascontiguousarray(field.data, dtype=np.float64),
        xreal=float(field.xreal),
        yreal=float(field.yreal),
        xoff=float(field.xoff),
        yoff=float(field.yoff),
        si_unit_xy=GwySIUnit(unitstr=str(field.si_unit_xy or "")),
        si_unit_z=GwySIUnit(unitstr=str(field.si_unit_z or "")),
    )
    title = path.stem or "field"
    container = GwyContainer({
        "/0/data": gwy_field,
        "/0/data/title": title,
    })
    container.tofile(str(path))


def _save_hdf5_generic(path: Path, field: DataField) -> None:
    """Write a single dataset ``/data`` with physical dimensions as dataset attrs.

    The layout is the mirror of :mod:`backend.importers.hdf5`: any 2-D numeric
    dataset is picked up and its attrs (``xreal``, ``yreal``, ``xoff``, ``yoff``,
    ``si_unit_xy``, ``si_unit_z``) reconstruct the DataField.
    """
    import h5py

    arr = np.ascontiguousarray(field.data, dtype=np.float64)
    with h5py.File(str(path), "w") as f:
        ds = f.create_dataset("data", data=arr)
        ds.attrs["xreal"] = float(field.xreal)
        ds.attrs["yreal"] = float(field.yreal)
        ds.attrs["xoff"]  = float(field.xoff)
        ds.attrs["yoff"]  = float(field.yoff)
        ds.attrs["si_unit_xy"] = str(field.si_unit_xy or "")
        ds.attrs["si_unit_z"]  = str(field.si_unit_z or "")


def _save_hdf5_ergo(path: Path, field: DataField) -> None:
    """Write an Asylum Research / Ergo-compatible HDF5 file.

    The layout mirrors :mod:`backend.importers.ergo_hdf5`:

    * The image dataset lives at
      ``Image/DataSet/Resolution 0/Frame 0/<title>/Image`` — the second-to-last
      path component is the channel name that the importer keys off.
    * A sidecar group at
      ``Image/DataSetInfo/Global/Channels/<title>/ImageDims`` carries
      ``DimScaling`` (a (2, 2) array of absolute physical ranges, Y-first),
      ``DimUnits`` (``[Y_unit, X_unit]``), and ``DataUnits`` (Z unit string).

    This makes the file openable by Asylum Ergo / Igor and round-trippable
    through our ergo_hdf5 importer.
    """
    import h5py

    arr = np.ascontiguousarray(field.data, dtype=np.float64)
    title = path.stem or "field"

    x_start = float(field.xoff)
    x_end   = float(field.xoff) + float(field.xreal)
    y_start = float(field.yoff)
    y_end   = float(field.yoff) + float(field.yreal)
    # DimScaling is stored Y-first to match the importer's expectations
    # (see ergo_hdf5.py:110-113).
    dim_scaling = np.array(
        [[y_start, y_end], [x_start, x_end]],
        dtype=np.float64,
    )
    # DimUnits is [Y_unit, X_unit]; the importer takes the X (second) entry
    # as the canonical lateral unit (see ergo_hdf5.py:129-135).
    xy_unit = str(field.si_unit_xy or "m")
    z_unit  = str(field.si_unit_z or "")
    dim_units = np.array([xy_unit, xy_unit], dtype=h5py.string_dtype())

    with h5py.File(str(path), "w") as f:
        ds = f.create_dataset(
            f"Image/DataSet/Resolution 0/Frame 0/{title}/Image",
            data=arr,
        )
        # Also write the generic attrs so non-Ergo readers still see physics.
        ds.attrs["xreal"] = float(field.xreal)
        ds.attrs["yreal"] = float(field.yreal)
        ds.attrs["xoff"]  = float(field.xoff)
        ds.attrs["yoff"]  = float(field.yoff)
        ds.attrs["si_unit_xy"] = xy_unit
        ds.attrs["si_unit_z"]  = z_unit

        dims_grp = f.create_group(
            f"Image/DataSetInfo/Global/Channels/{title}/ImageDims"
        )
        dims_grp.attrs["DimScaling"] = dim_scaling
        dims_grp.attrs["DimUnits"]   = dim_units
        dims_grp.attrs["DataUnits"]  = z_unit
