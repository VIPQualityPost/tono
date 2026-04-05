"""
Tests for the exporter registry and the round-trippable DataField formats.

The Save node's format-specific behavior is covered in test_save_generic
(tests/node_tests/save.py). This module focuses on:

  1. Registry contract — every exporter module satisfies the protocol.
  2. Dispatch — type_name_for_value classifies values correctly and
     get_exporter returns a matching module.
  3. Round-trip — GWY and TIFF (data) preserve xreal/yreal/units/data.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from backend.data_types import (
    DataField,
    DataTable,
    ImageData,
    LineData,
    MeshModel,
    RecordTable,
)


def test_exporter_registry_contract():
    """Every registered exporter module must expose the required attributes."""
    from backend.exporters import _REGISTRY
    from backend.exporters._base import FormatSpec

    assert _REGISTRY, "Registry must not be empty"
    seen_modules = {mod for (mod, _) in _REGISTRY.values()}
    for module in seen_modules:
        assert hasattr(module, "accepted_types")
        assert hasattr(module, "FORMATS")
        assert hasattr(module, "save")
        assert isinstance(module.accepted_types, tuple)
        assert all(isinstance(t, str) and t.isupper() for t in module.accepted_types)
        assert isinstance(module.FORMATS, dict)
        for name, spec in module.FORMATS.items():
            assert isinstance(name, str) and name
            assert isinstance(spec, FormatSpec)
            assert spec.ext.startswith(".")


def test_type_name_for_value_classification():
    from backend.exporters import type_name_for_value

    assert type_name_for_value(DataField(data=np.zeros((4, 4)))) == "DATA_FIELD"
    assert type_name_for_value(np.zeros((4, 4))) == "IMAGE"
    assert type_name_for_value(np.zeros((4, 4, 3), dtype=np.uint8)) == "IMAGE"
    assert type_name_for_value(ImageData(np.zeros((4, 4), dtype=np.uint8))) == "IMAGE"
    assert type_name_for_value(np.zeros(8)) == "LINE"
    assert type_name_for_value(LineData(data=np.zeros(8))) == "LINE"
    assert type_name_for_value(RecordTable([{"a": 1}])) == "RECORD_TABLE"
    assert type_name_for_value(DataTable([{"a": 1}])) == "DATA_TABLE"
    assert type_name_for_value(1.25) == "FLOAT"
    assert type_name_for_value(np.float64(0.5)) == "FLOAT"
    mesh = MeshModel(
        vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
        faces=np.array([[0, 1, 2]], dtype=np.int32),
    )
    assert type_name_for_value(mesh) == "MESH_MODEL"

    try:
        type_name_for_value(object())
        assert False, "Expected ValueError for unsupported type"
    except ValueError:
        pass


def test_get_exporter_known_and_unknown():
    from backend.exporters import get_exporter

    mod, spec = get_exporter("DATA_FIELD", "GWY")
    assert spec.ext == ".gwy"
    assert spec.round_trip is True

    mod, spec = get_exporter("DATA_FIELD", "TIFF")
    assert spec.ext == ".tiff"
    # Legacy preview path — not round-trippable.
    assert spec.round_trip is False

    mod, spec = get_exporter("DATA_FIELD", "TIFF (data)")
    assert spec.round_trip is True

    try:
        get_exporter("DATA_FIELD", "DOES_NOT_EXIST")
        assert False, "Expected ValueError for unknown format"
    except ValueError:
        pass

    try:
        get_exporter("FLOAT", "GWY")
        assert False, "Expected ValueError for type/format mismatch"
    except ValueError:
        pass


def test_available_formats_includes_new_datafield_formats():
    from backend.exporters import available_formats

    formats = available_formats("DATA_FIELD")
    assert "TIFF" in formats
    assert "TIFF (data)" in formats
    assert "GWY" in formats
    assert "PNG" in formats
    assert "NPZ" in formats
    assert "HDF5" in formats
    assert "HDF5 (Ergo)" in formats


def test_datafield_gwy_round_trip():
    """Writing a DataField to .gwy and reloading via the importer preserves everything."""
    from backend.importers import gwy as gwy_importer
    from backend.nodes.save import Save

    rng = np.random.default_rng(7)
    data = rng.standard_normal((32, 48)).astype(np.float64) * 1e-9
    field = DataField(
        data=data,
        xreal=3.2e-6,
        yreal=2.4e-6,
        xoff=1.1e-7,
        yoff=-5.5e-7,
        si_unit_xy="m",
        si_unit_z="m",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "topo"
        Save().save(filename=str(path), format="GWY", value=field)
        out_path = path.with_suffix(".gwy")
        assert out_path.exists()

        reloaded = gwy_importer.load(out_path)
        assert len(reloaded) == 1
        rf = reloaded[0]
        assert rf.data.shape == field.data.shape
        assert np.allclose(rf.data, field.data)
        assert np.isclose(rf.xreal, field.xreal)
        assert np.isclose(rf.yreal, field.yreal)
        assert np.isclose(rf.xoff, field.xoff)
        assert np.isclose(rf.yoff, field.yoff)
        assert rf.si_unit_xy == "m"
        assert rf.si_unit_z == "m"

        # channel_names() should return the stem we used as the title
        names = gwy_importer.channel_names(out_path)
        assert names == ["topo"]


def test_datafield_tiff_data_round_trip():
    """TIFF (data) writes float64 pixels + JSON metadata; we verify both."""
    import tifffile

    from backend.nodes.save import Save

    rng = np.random.default_rng(11)
    data = rng.standard_normal((24, 36)).astype(np.float64) * 1e-8
    field = DataField(
        data=data,
        xreal=5e-6,
        yreal=3e-6,
        xoff=0.0,
        yoff=0.0,
        si_unit_xy="m",
        si_unit_z="V",
        colormap="viridis",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "field"
        Save().save(filename=str(path), format="TIFF (data)", value=field)
        out_path = path.with_suffix(".tiff")
        assert out_path.exists()

        with tifffile.TiffFile(out_path) as tif:
            arr = tif.asarray()
            desc = tif.pages[0].tags["ImageDescription"].value

        assert arr.dtype == np.float64
        assert arr.shape == field.data.shape
        assert np.allclose(arr, field.data)

        meta = json.loads(desc)["tono"]
        assert meta["xreal"] == field.xreal
        assert meta["yreal"] == field.yreal
        assert meta["si_unit_xy"] == "m"
        assert meta["si_unit_z"] == "V"
        assert meta["domain"] == "spatial"


def test_datafield_hdf5_generic_round_trip():
    """HDF5 (generic) writes /data + attrs that our hdf5 importer reads back."""
    from backend.importers import hdf5 as hdf5_importer
    from backend.nodes.save import Save

    rng = np.random.default_rng(23)
    data = rng.standard_normal((20, 28)).astype(np.float64) * 1e-7
    field = DataField(
        data=data,
        xreal=4.8e-6,
        yreal=3.2e-6,
        xoff=1.5e-7,
        yoff=-2.5e-7,
        si_unit_xy="m",
        si_unit_z="V",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "topo"
        Save().save(filename=str(path), format="HDF5", value=field)
        out_path = path.with_suffix(".h5")
        assert out_path.exists()

        reloaded = hdf5_importer.load(out_path)
        assert len(reloaded) == 1
        rf = reloaded[0]
        assert rf.data.shape == field.data.shape
        assert np.allclose(rf.data, field.data)
        assert np.isclose(rf.xreal, field.xreal)
        assert np.isclose(rf.yreal, field.yreal)
        assert np.isclose(rf.xoff, field.xoff)
        assert np.isclose(rf.yoff, field.yoff)
        assert rf.si_unit_xy == "m"
        assert rf.si_unit_z == "V"


def test_datafield_hdf5_ergo_round_trip():
    """HDF5 (Ergo) writes the Asylum sidecar layout and round-trips via ergo_hdf5."""
    import h5py

    from backend.importers import ergo_hdf5 as ergo_importer
    from backend.nodes.save import Save

    rng = np.random.default_rng(29)
    data = rng.standard_normal((16, 24)).astype(np.float64) * 1e-9
    field = DataField(
        data=data,
        xreal=2.5e-6,
        yreal=1.8e-6,
        xoff=0.5e-7,
        yoff=-1.1e-7,
        si_unit_xy="m",
        si_unit_z="N",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "topo"
        Save().save(filename=str(path), format="HDF5 (Ergo)", value=field)
        out_path = path.with_suffix(".h5")
        assert out_path.exists()

        # Sanity-check the layout: the dataset lives under
        # Image/DataSet/Resolution 0/Frame 0/<title>/Image, and the sidecar
        # group under Image/DataSetInfo/Global/Channels/<title>/ImageDims.
        with h5py.File(str(out_path), "r") as f:
            assert "Image/DataSet/Resolution 0/Frame 0/topo/Image" in f
            dims = f["Image/DataSetInfo/Global/Channels/topo/ImageDims"]
            scaling = np.asarray(dims.attrs["DimScaling"])
            assert scaling.shape == (2, 2)
            # DimScaling is Y-first: [[y_start, y_end], [x_start, x_end]]
            assert np.isclose(scaling[1, 1] - scaling[1, 0], field.xreal)
            assert np.isclose(scaling[0, 1] - scaling[0, 0], field.yreal)

        reloaded = ergo_importer.load(out_path)
        assert len(reloaded) == 1
        rf = reloaded[0]
        assert rf.data.shape == field.data.shape
        assert np.allclose(rf.data, field.data)
        assert np.isclose(rf.xreal, field.xreal)
        assert np.isclose(rf.yreal, field.yreal)
        assert np.isclose(rf.xoff, field.xoff)
        assert np.isclose(rf.yoff, field.yoff)
        assert rf.si_unit_xy == "m"
        assert rf.si_unit_z == "N"


def test_tiff_preview_is_still_rgb_uint8():
    """The legacy TIFF format for DATA_FIELD must keep producing 8-bit RGB."""
    import tifffile

    from backend.nodes.save import Save

    field = DataField(
        data=np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float64),
        xreal=1e-6, yreal=1e-6, si_unit_xy="m", si_unit_z="m",
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "preview"
        Save().save(filename=str(path), format="TIFF", value=field)
        arr = tifffile.imread(str(path.with_suffix(".tiff")))
        assert arr.dtype == np.uint8
        assert arr.shape == (2, 2, 3)
