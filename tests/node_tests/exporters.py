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

        # Per-layer metadata lives under tono.layers[*]; a single-layer save
        # still produces the same shape, just with one entry.
        meta = json.loads(desc)["tono"]
        assert meta["version"] == 1
        assert len(meta["layers"]) == 1
        layer0 = meta["layers"][0]
        assert layer0["kind"] == "data_field"
        assert layer0["xreal"] == field.xreal
        assert layer0["yreal"] == field.yreal
        assert layer0["si_unit_xy"] == "m"
        assert layer0["si_unit_z"] == "V"
        assert layer0["domain"] == "spatial"


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


def test_save_multi_layer_tiff_data():
    """TIFF (data) with extra layers writes multi-page float64 with per-layer metadata."""
    import tifffile

    from backend.nodes.save import Save

    rng = np.random.default_rng(41)
    primary = DataField(
        data=rng.standard_normal((16, 20)).astype(np.float64) * 1e-9,
        xreal=3e-6, yreal=2e-6, si_unit_xy="m", si_unit_z="m",
    )
    layer2 = DataField(
        data=rng.standard_normal((16, 20)).astype(np.float64) * 1e-12,
        xreal=3e-6, yreal=2e-6, si_unit_xy="m", si_unit_z="N",
    )
    layer3 = DataField(
        data=rng.standard_normal((16, 20)).astype(np.float64),
        xreal=3e-6, yreal=2e-6, si_unit_xy="m", si_unit_z="V",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "stack"
        Save().save(
            filename=str(path),
            format="TIFF (data)",
            value=primary,
            field_0=layer2,
            field_1=layer3,
            primary_name="height",
            layer_name_0="force",
            layer_name_1="potential",
        )
        out_path = path.with_suffix(".tiff")
        assert out_path.exists()

        with tifffile.TiffFile(out_path) as tif:
            assert len(tif.pages) == 3
            meta = json.loads(tif.pages[0].tags["ImageDescription"].value)["tono"]
            assert len(meta["layers"]) == 3
            assert [layer["name"] for layer in meta["layers"]] == ["height", "force", "potential"]
            assert meta["layers"][1]["si_unit_z"] == "N"
            assert meta["layers"][2]["si_unit_z"] == "V"
            assert tif.pages[0].asarray().shape == (16, 20)
            assert tif.pages[1].asarray().shape == (16, 20)
            assert np.allclose(tif.pages[0].asarray(), primary.data)
            assert np.allclose(tif.pages[2].asarray(), layer3.data)


def test_save_multi_layer_npz_named_keys():
    """Multi-layer NPZ uses safe-identifier keys from layer names."""
    from backend.nodes.save import Save

    rng = np.random.default_rng(47)
    primary = DataField(data=rng.standard_normal((8, 8)).astype(np.float64))
    layer2 = DataField(data=rng.standard_normal((8, 8)).astype(np.float64))
    annotated = np.zeros((12, 12, 3), dtype=np.uint8)
    annotated[..., 0] = 255

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "stack"
        Save().save(
            filename=str(path),
            format="NPZ",
            value=primary,
            field_0=layer2,
            field_1=annotated,
            primary_name="height map",
            layer_name_0="force-retrace",
            layer_name_1="annotated overview",
        )
        out_path = path.with_suffix(".npz")
        assert out_path.exists()

        npz = np.load(out_path)
        # Non-identifier characters collapse to underscores.
        assert set(npz.files) == {"height_map", "force_retrace", "annotated_overview"}
        assert np.allclose(npz["height_map"], primary.data)
        assert np.allclose(npz["force_retrace"], layer2.data)
        assert np.array_equal(npz["annotated_overview"], annotated)


def test_save_multi_layer_tiff_preview_rejected():
    """Single-layer-only formats must reject extra layers with a clear error."""
    from backend.nodes.save import Save

    field_a = DataField(data=np.zeros((4, 4)))
    field_b = DataField(data=np.ones((4, 4)))
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "preview"
        try:
            Save().save(
                filename=str(path),
                format="TIFF",  # preview format, single-layer only
                value=field_a,
                field_0=field_b,
            )
            assert False, "TIFF preview must reject extra layers"
        except ValueError as exc:
            assert "single layer" in str(exc).lower()

        try:
            Save().save(
                filename=str(path),
                format="PNG",
                value=field_a,
                field_0=field_b,
            )
            assert False, "PNG must reject extra layers"
        except ValueError as exc:
            assert "single layer" in str(exc).lower()


def test_save_multi_channel_gwy_round_trip():
    """A multi-channel GWY save round-trips via the gwy importer."""
    from backend.importers import gwy as gwy_importer
    from backend.nodes.save import Save

    rng = np.random.default_rng(53)
    primary = DataField(
        data=rng.standard_normal((24, 32)).astype(np.float64) * 1e-9,
        xreal=4e-6, yreal=3e-6, si_unit_xy="m", si_unit_z="m",
    )
    layer2 = DataField(
        data=rng.standard_normal((24, 32)).astype(np.float64) * 1e-11,
        xreal=4e-6, yreal=3e-6, si_unit_xy="m", si_unit_z="N",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "topo"
        Save().save(
            filename=str(path),
            format="GWY",
            value=primary,
            field_0=layer2,
            primary_name="height",
            layer_name_0="adhesion",
        )
        out_path = path.with_suffix(".gwy")
        assert out_path.exists()

        reloaded = gwy_importer.load(out_path)
        assert len(reloaded) == 2
        names = gwy_importer.channel_names(out_path)
        assert set(names) == {"height", "adhesion"}
        # GWY does not guarantee iteration order across channels, so match
        # each input by content rather than by position.
        assert any(np.allclose(f.data, primary.data) for f in reloaded)
        assert any(np.allclose(f.data, layer2.data) for f in reloaded)
        for f in reloaded:
            assert np.isclose(f.xreal, 4e-6)
            assert np.isclose(f.yreal, 3e-6)


def test_save_multi_channel_hdf5_round_trip():
    """Multi-channel generic HDF5 round-trips via the hdf5 importer."""
    from backend.importers import hdf5 as hdf5_importer
    from backend.nodes.save import Save

    rng = np.random.default_rng(59)
    primary = DataField(
        data=rng.standard_normal((12, 18)).astype(np.float64) * 1e-7,
        xreal=2e-6, yreal=1.5e-6, si_unit_xy="m", si_unit_z="V",
    )
    layer2 = DataField(
        data=rng.standard_normal((12, 18)).astype(np.float64) * 1e-9,
        xreal=2e-6, yreal=1.5e-6, si_unit_xy="m", si_unit_z="A",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "stack"
        Save().save(
            filename=str(path),
            format="HDF5",
            value=primary,
            field_0=layer2,
            primary_name="potential",
            layer_name_0="current",
        )
        out_path = path.with_suffix(".h5")
        assert out_path.exists()

        reloaded = hdf5_importer.load(out_path)
        assert len(reloaded) == 2
        # Identify the two channels by their unique z-units.
        by_unit = {rf.si_unit_z: rf for rf in reloaded}
        assert set(by_unit.keys()) == {"V", "A"}
        assert np.allclose(by_unit["V"].data, primary.data)
        assert np.allclose(by_unit["A"].data, layer2.data)


def test_save_multi_channel_hdf5_ergo_round_trip():
    """Multi-channel Ergo-layout HDF5 round-trips via the ergo_hdf5 importer."""
    from backend.importers import ergo_hdf5 as ergo_importer
    from backend.nodes.save import Save

    rng = np.random.default_rng(61)
    primary = DataField(
        data=rng.standard_normal((10, 14)).astype(np.float64) * 1e-9,
        xreal=1.5e-6, yreal=1e-6, si_unit_xy="m", si_unit_z="m",
    )
    layer2 = DataField(
        data=rng.standard_normal((10, 14)).astype(np.float64) * 1e-11,
        xreal=1.5e-6, yreal=1e-6, si_unit_xy="m", si_unit_z="N",
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "topo"
        Save().save(
            filename=str(path),
            format="HDF5 (Ergo)",
            value=primary,
            field_0=layer2,
            primary_name="height",
            layer_name_0="adhesion",
        )
        out_path = path.with_suffix(".h5")
        assert out_path.exists()

        reloaded = ergo_importer.load(out_path)
        assert len(reloaded) == 2
        by_unit = {rf.si_unit_z: rf for rf in reloaded}
        assert set(by_unit.keys()) == {"m", "N"}
        assert np.allclose(by_unit["m"].data, primary.data)
        assert np.allclose(by_unit["N"].data, layer2.data)


def test_save_gwy_rejects_image_layer():
    """GWY/HDF5 formats must error cleanly on non-DataField layers."""
    from backend.nodes.save import Save

    field = DataField(data=np.zeros((4, 4)))
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "topo"
        try:
            Save().save(
                filename=str(path),
                format="GWY",
                value=field,
                field_0=image,
            )
            assert False, "GWY must reject non-DataField layers"
        except ValueError as exc:
            assert "DataField" in str(exc) or "data field" in str(exc).lower()


def test_save_ignores_extra_layers_for_non_stackable_types():
    """Stray field_N kwargs must be ignored when value is a scalar/line/table."""
    from backend.nodes.save import Save

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "scalar"
        # field_0 is connected but should be silently ignored for a FLOAT value.
        Save().save(
            filename=str(path),
            format="TXT",
            value=1.25,
            field_0=DataField(data=np.zeros((4, 4))),
        )
        assert Path(tmpdir, "scalar.txt").read_text(encoding="utf-8").strip() == "1.25"


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
