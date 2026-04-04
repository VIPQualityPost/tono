"""
Tests for backend/importers/ — the importer registry and each importer module.
"""

import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

from backend.data_types import DataField

FIXTURES = Path(__file__).parent.parent / "fixtures"
_SUBMODULE_HINT = (
    "run `git submodule update --init tests/fixtures` to fetch the tono-test-data submodule"
)


# ── Registry ─────────────────────────────────────────────────────────────────

class TestRegistry:
    def test_get_importer_known_extensions(self):
        from backend.importers import get_importer
        for ext in (".gwy", ".sxm", ".ibw", ".npy", ".npz",
                    ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp",
                    ".h5", ".hdf5", ".he5"):
            assert get_importer(ext) is not None, f"No importer registered for {ext}"

    def test_get_importer_unknown_extension(self):
        from backend.importers import get_importer
        assert get_importer(".xyz") is None
        assert get_importer(".csv") is None

    def test_get_importer_case_insensitive(self):
        from backend.importers import get_importer
        assert get_importer(".NPY") is get_importer(".npy")
        assert get_importer(".GWY") is get_importer(".gwy")

    def test_all_extensions_returns_frozenset(self):
        from backend.importers import all_extensions
        exts = all_extensions()
        assert isinstance(exts, frozenset)
        assert ".npy" in exts
        assert ".gwy" in exts

    def test_calibrated_extensions(self):
        from backend.importers import calibrated_extensions
        cal = calibrated_extensions()
        # SPM and HDF5 are calibrated
        assert ".gwy" in cal
        assert ".sxm" in cal
        assert ".ibw" in cal
        assert ".h5" in cal
        # Images/arrays are not
        assert ".png" not in cal
        assert ".npy" not in cal

    def test_each_importer_has_required_interface(self):
        from backend.importers import _IMPORTERS
        for mod in _IMPORTERS:
            assert hasattr(mod, "extensions"), f"{mod.__name__} missing extensions"
            assert hasattr(mod, "calibrated"), f"{mod.__name__} missing calibrated"
            assert callable(getattr(mod, "load", None)), f"{mod.__name__} missing load()"
            assert callable(getattr(mod, "channel_names", None)), f"{mod.__name__} missing channel_names()"
            assert isinstance(mod.extensions, frozenset)
            assert isinstance(mod.calibrated, bool)


# ── array_image importer ──────────────────────────────────────────────────────

class TestArrayImageImporter:
    def setup_method(self):
        import backend.importers.array_image as mod
        self.mod = mod

    def test_npy_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = np.random.default_rng(0).standard_normal((32, 48))
            path = Path(tmp) / "data.npy"
            np.save(path, data)
            fields = self.mod.load(path)
            assert len(fields) == 1
            assert isinstance(fields[0], DataField)
            assert np.allclose(fields[0].data, data)

    def test_npz_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = np.random.default_rng(1).standard_normal((16, 16))
            path = Path(tmp) / "data.npz"
            np.savez(path, arr=data)
            fields = self.mod.load(path)
            assert len(fields) == 1
            assert np.allclose(fields[0].data, data)

    def test_png_grayscale(self):
        from PIL import Image as PILImage
        with tempfile.TemporaryDirectory() as tmp:
            arr = np.random.default_rng(2).integers(0, 256, (24, 32), dtype=np.uint8)
            path = Path(tmp) / "gray.png"
            PILImage.fromarray(arr).save(path)
            fields = self.mod.load(path)
            assert len(fields) == 1
            assert fields[0].data.shape == (24, 32)
            assert fields[0].data.dtype == np.float64

    def test_png_rgb_converted_to_grayscale(self):
        from PIL import Image as PILImage
        with tempfile.TemporaryDirectory() as tmp:
            arr = np.random.default_rng(3).integers(0, 256, (16, 16, 3), dtype=np.uint8)
            path = Path(tmp) / "rgb.png"
            PILImage.fromarray(arr).save(path)
            fields = self.mod.load(path)
            assert fields[0].data.shape == (16, 16)

    def test_not_calibrated(self):
        assert self.mod.calibrated is False

    def test_channel_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.npy"
            np.save(path, np.zeros((4, 4)))
            assert self.mod.channel_names(path) == ["field"]

    def test_fixture_npy(self):
        path = FIXTURES / "nanoparticles.npy"
        if not path.exists():
            pytest.skip(f"nanoparticles.npy fixture not available — {_SUBMODULE_HINT}")
        fields = self.mod.load(path)
        assert len(fields) == 1
        assert fields[0].data.ndim == 2


# ── ibw importer ─────────────────────────────────────────────────────────────

class TestIBWImporter:
    def setup_method(self):
        import backend.importers.ibw as mod
        self.mod = mod
        self.fixture = FIXTURES / "Bacteria.ibw"

    def test_calibrated(self):
        assert self.mod.calibrated is True

    def test_extensions(self):
        assert ".ibw" in self.mod.extensions

    def test_load_fixture(self):
        if not self.fixture.exists():
            pytest.skip(f"Bacteria.ibw fixture not available — {_SUBMODULE_HINT}")
        fields = self.mod.load(self.fixture)
        assert len(fields) == 4
        for f in fields:
            assert isinstance(f, DataField)
            assert f.data.ndim == 2
            assert f.data.dtype == np.float64
            assert f.xreal > 0
            assert f.yreal > 0

    def test_channel_names_fixture(self):
        if not self.fixture.exists():
            pytest.skip(f"Bacteria.ibw fixture not available — {_SUBMODULE_HINT}")
        names = self.mod.channel_names(self.fixture)
        assert len(names) == 4
        assert all(isinstance(n, str) for n in names)


# ── hdf5 importer (generic) ──────────────────────────────────────────────────

class TestHDF5Importer:
    def setup_method(self):
        pytest.importorskip("h5py")
        import backend.importers.hdf5 as mod
        self.mod = mod

    def test_calibrated(self):
        assert self.mod.calibrated is True

    def test_extensions(self):
        assert {".h5", ".hdf5", ".he5"} <= self.mod.extensions

    def test_load_single_channel(self):
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            data = np.random.default_rng(10).standard_normal((32, 32))
            path = Path(tmp) / "test.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("channel", data=data)
            fields = self.mod.load(path)
            assert len(fields) == 1
            assert np.allclose(fields[0].data, data)
            assert fields[0].data.dtype == np.float64

    def test_load_physical_attrs(self):
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cal.h5"
            with h5py.File(path, "w") as f:
                ds = f.create_dataset("topo", data=np.zeros((16, 16)))
                ds.attrs["xreal"] = 5e-6
                ds.attrs["yreal"] = 5e-6
                ds.attrs["si_unit_z"] = "V"
            fields = self.mod.load(path)
            assert fields[0].xreal == pytest.approx(5e-6)
            assert fields[0].si_unit_z == "V"

    def test_load_fallback_attrs(self):
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fallback.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("channel", data=np.zeros((8, 8)))
            fields = self.mod.load(path)
            assert fields[0].xreal == pytest.approx(1e-6)
            assert fields[0].si_unit_xy == "m"

    def test_empty_file_raises(self):
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("vec", data=np.zeros((10,)))
            with pytest.raises(ValueError, match="No 2-D"):
                self.mod.load(path)

    def test_channel_names_top_level(self):
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "named.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("height", data=np.zeros((8, 8)))
                f.create_dataset("phase", data=np.zeros((8, 8)))
            names = self.mod.channel_names(path)
            assert set(names) == {"height", "phase"}

    def test_channel_names_nested(self):
        # Nested datasets return second-to-last path component.
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("scan/height/data", data=np.zeros((8, 8)))
                f.create_dataset("scan/phase/data", data=np.zeros((8, 8)))
            names = self.mod.channel_names(path)
            assert set(names) == {"height", "phase"}


# ── ergo_hdf5 importer (Asylum Research / Ergo format) ───────────────────────

class TestErgoHDF5Importer:
    def setup_method(self):
        pytest.importorskip("h5py")
        import backend.importers.ergo_hdf5 as mod
        self.mod = mod

    def _make_h5(self, tmp: Path, data: np.ndarray, name: str = "channel",
                 attrs: dict | None = None) -> Path:
        import h5py
        path = tmp / "test.h5"
        with h5py.File(path, "w") as f:
            ds = f.create_dataset(name, data=data)
            for k, v in (attrs or {}).items():
                ds.attrs[k] = v
        return path

    def test_calibrated(self):
        assert self.mod.calibrated is True

    def test_extensions(self):
        assert {".h5", ".hdf5", ".he5"} <= self.mod.extensions

    def test_load_single_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = np.random.default_rng(10).standard_normal((32, 32))
            path = self._make_h5(Path(tmp), data)
            fields = self.mod.load(path)
            assert len(fields) == 1
            assert np.allclose(fields[0].data, data)
            assert fields[0].data.dtype == np.float64

    def test_load_physical_attrs(self):
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            data = np.zeros((16, 16))
            path = Path(tmp) / "cal.h5"
            with h5py.File(path, "w") as f:
                ds = f.create_dataset("topo", data=data)
                ds.attrs["xreal"] = 5e-6
                ds.attrs["yreal"] = 5e-6
                ds.attrs["si_unit_xy"] = "m"
                ds.attrs["si_unit_z"] = "V"
            fields = self.mod.load(path)
            assert fields[0].xreal == pytest.approx(5e-6)
            assert fields[0].yreal == pytest.approx(5e-6)
            assert fields[0].si_unit_z == "V"

    def test_load_fallback_attrs(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = np.zeros((8, 8))
            path = self._make_h5(Path(tmp), data)
            fields = self.mod.load(path)
            # Default fallbacks when no AR sidecar is present
            assert fields[0].xreal == pytest.approx(1e-6)
            assert fields[0].si_unit_xy == "m"

    def test_load_multiple_channels(self):
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "multi.h5"
            data_a = np.ones((16, 16))
            data_b = np.zeros((16, 16))
            with h5py.File(path, "w") as f:
                f.create_dataset("height", data=data_a)
                f.create_dataset("phase", data=data_b)
            fields = self.mod.load(path)
            assert len(fields) == 2
            shapes = {f.data.shape for f in fields}
            assert shapes == {(16, 16)}

    def test_ignores_non_2d_datasets(self):
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mixed.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("topo", data=np.zeros((16, 16)))
                f.create_dataset("vector", data=np.zeros((10,)))    # 1-D, ignored
                f.create_dataset("volume", data=np.zeros((4, 4, 4)))  # 3-D, ignored
            fields = self.mod.load(path)
            assert len(fields) == 1

    def test_empty_file_raises(self):
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("vec", data=np.zeros((10,)))
            with pytest.raises(ValueError, match="No 2-D"):
                self.mod.load(path)

    def test_channel_names_top_level(self):
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "named.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("height", data=np.zeros((8, 8)))
                f.create_dataset("phase", data=np.zeros((8, 8)))
            names = self.mod.channel_names(path)
            assert set(names) == {"height", "phase"}

    def test_channel_names_strips_leaf(self):
        # "/image" leaf is stripped; display name is second-to-last component.
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("scan/adhesion:retrace/image", data=np.zeros((8, 8)))
                f.create_dataset("scan/phase:retrace/image", data=np.zeros((8, 8)))
            names = self.mod.channel_names(path)
            assert set(names) == {"adhesion:retrace", "phase:retrace"}

    def test_channel_names_thumbnails_always_filtered(self):
        # All thumbnail datasets are hidden, including global ones.
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "thumbs.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("data/adhesion/image", data=np.zeros((8, 8)))
                f.create_dataset("info/channels/adhesion/thumbnail", data=np.zeros((8, 8)))
                f.create_dataset("info/global/thumbnail", data=np.zeros((8, 8)))
            names = self.mod.channel_names(path)
            assert names == ["adhesion"]

    def test_channel_names_sorted_alphabetically(self):
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "order.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("data/zzz/image", data=np.zeros((8, 8)))
                f.create_dataset("data/aaa/image", data=np.zeros((8, 8)))
            names = self.mod.channel_names(path)
            assert names == ["aaa", "zzz"]

    def test_channel_names_deduplication(self):
        # Two kept datasets with the same second-to-last name get disambiguated.
        import h5py
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dup.h5"
            with h5py.File(path, "w") as f:
                f.create_dataset("dataset/adhesion/imageA", data=np.zeros((8, 8)))
                f.create_dataset("datasetinfo/adhesion/imageB", data=np.zeros((8, 8)))
            names = self.mod.channel_names(path)
            assert set(names) == {"adhesion/imageA", "adhesion/imageB"}

    def test_he5_extension_registered(self):
        from backend.importers import get_importer
        assert get_importer(".he5") is self.mod
