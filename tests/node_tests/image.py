import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image as PILImage

from backend.data_types import DataField


def test_load_file():
    from backend.nodes.image import Image as ImageNode
    node = ImageNode()

    with tempfile.TemporaryDirectory() as tmpdir:
        arr = np.random.default_rng(1).integers(0, 256, (48, 64), dtype=np.uint8)
        img = PILImage.fromarray(arr, mode="L")
        path = os.path.join(tmpdir, "test_gray.png")
        img.save(path)

        result = node.load(filename=path)
        assert len(result) == 2
        assert isinstance(result[0], str)
        field = result[1]
        assert field.data.shape == (48, 64)
        assert field.data.dtype == np.float64

        arr_rgb = np.random.default_rng(2).integers(0, 256, (32, 32, 3), dtype=np.uint8)
        img_rgb = PILImage.fromarray(arr_rgb, mode="RGB")
        path_rgb = os.path.join(tmpdir, "test_rgb.png")
        img_rgb.save(path_rgb)

        result_rgb = node.load(filename=path_rgb)
        assert len(result_rgb) == 2
        assert result_rgb[1].data.shape == (32, 32)

        data_npy = np.random.default_rng(3).standard_normal((50, 60))
        path_npy = os.path.join(tmpdir, "test.npy")
        np.save(path_npy, data_npy)

        result_npy = node.load(filename=path_npy)
        assert np.allclose(result_npy[1].data, data_npy)

        custom_colormap = {
            "mode": "custom",
            "stops": [
                {"position": 0.0, "color": "#000000"},
                {"position": 0.5, "color": "#ff0000"},
                {"position": 1.0, "color": "#ffffff"},
            ],
        }
        result_custom = node.load(filename=path, colormap_map=custom_colormap)
        assert isinstance(result_custom[1].colormap, dict)
        assert result_custom[1].colormap["mode"] == "custom"
        assert len(result_custom[1].colormap["stops"]) == 3

        result_from_path = node.load(filename="", path=path)
        assert len(result_from_path) == 2
        assert result_from_path[1].data.shape == (48, 64)


def test_load_file_npz():
    from backend.nodes.image import Image
    node = Image()
    with tempfile.TemporaryDirectory() as tmpdir:
        data = np.random.default_rng(99).standard_normal((30, 40))
        path = os.path.join(tmpdir, "test.npz")
        np.savez(path, my_array=data)

        result = node.load(filename=path)
        assert len(result) == 2
        assert np.allclose(result[1].data, data)


def test_load_file_cache():
    from backend.nodes.image import Image
    node = Image()
    Image._load_fields_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        data = np.arange(16, dtype=np.float64).reshape(4, 4)
        path = os.path.join(tmpdir, "cached.npy")
        np.save(path, data)

        import backend.importers.array_image as _ai
        with patch.object(_ai, "load", wraps=_ai.load) as loader:
            _, first = node.load(filename=path)
            _, second = node.load(filename=path)
            assert loader.call_count == 1

        assert np.allclose(first.data, data)
        assert np.allclose(second.data, data)
        assert first is not second
        first.data[0, 0] = -999.0

        _, third = node.load(filename=path)
        assert third.data[0, 0] == data[0, 0]

    Image._load_fields_cached.cache_clear()


def test_load_file_not_found():
    from backend.nodes.image import Image
    node = Image()
    try:
        node.load(filename="/nonexistent/path/file.png")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_load_file_unsupported():
    from backend.nodes.image import Image
    node = Image()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.xyz")
        with open(path, "w") as f:
            f.write("hello")
        try:
            node.load(filename=path)
            assert False, "Should have raised an error for .xyz"
        except Exception:
            pass


def test_load_file_warning():
    from backend.nodes.image import Image as ImageNode
    from backend.execution_context import execution_callbacks, active_node
    node = ImageNode()
    warnings = []

    with tempfile.TemporaryDirectory() as tmpdir, \
         execution_callbacks(warning=lambda nid, msg: warnings.append(msg)), \
         active_node("test"):
        arr = np.random.default_rng(10).integers(0, 256, (16, 16), dtype=np.uint8)
        img = PILImage.fromarray(arr)
        path = os.path.join(tmpdir, "test.png")
        img.save(path)

        result = node.load(filename=path)
        assert len(result) == 2
        assert len(warnings) == 1
        assert "Uncalibrated" in warnings[0]


def test_load_file_ibw():
    from backend.nodes.image import Image
    node = Image()
    demo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "demo"))
    # Use first available .ibw file in demo
    ibw_path = None
    for candidate in ["Calcite.ibw", "DNA.ibw", "nanoparticles.npy"]:
        p = os.path.join(demo_dir, candidate)
        if os.path.exists(p):
            ibw_path = p
            break
    if ibw_path is None:
        return

    result = node.load(filename=ibw_path)
    assert len(result) >= 2
    for item in result[1:]:
        assert isinstance(item, DataField)
        assert item.data.dtype == np.float64
        assert item.xreal > 0


def test_load_all_channels_exposed():
    """Every channel of a multi-channel file gets its own output, in order."""
    from backend.nodes.image import Image
    from backend.nodes.helpers import list_channels
    node = Image()

    demo_bacteria = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "demo", "Bacteria.ibw"))
    if not os.path.exists(demo_bacteria):
        return

    result = node.load(filename=demo_bacteria)
    fields = result[1:]
    assert isinstance(result[0], str)
    # 4 channels → path output + 4 DataField outputs (no 3-channel cap).
    assert len(fields) == 4
    names = [entry["name"] for entry in list_channels(demo_bacteria)]
    assert names == ["HeightTrace", "AmplitudeTrace", "PhaseTrace", "HeightTraceMod0"]
    from backend.importers.ibw import load as ibw_load
    expected = ibw_load(demo_bacteria)
    for slot, field in enumerate(fields):
        assert np.allclose(field.data, expected[slot].data)


def test_load_empty_filename_raises():
    from backend.nodes.image import Image
    node = Image()
    try:
        node.load(filename="")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_load_directory_raises():
    from backend.nodes.image import Image
    node = Image()
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            node.load(filename=tmpdir)
            assert False, "Expected IsADirectoryError"
        except IsADirectoryError:
            pass


def test_load_float_tiff():
    """float32 TIFF images should be converted to float64 (covers non-uint8 branch)."""
    import tifffile
    from backend.nodes.image import Image
    node = Image()
    Image._load_fields_cached.cache_clear()
    with tempfile.TemporaryDirectory() as tmpdir:
        arr = np.random.default_rng(42).random((16, 16)).astype(np.float32)
        path = os.path.join(tmpdir, "float.tiff")
        tifffile.imwrite(path, arr)

        result = node.load(filename=path)
        assert len(result) == 2
        assert result[1].data.dtype == np.float64
    Image._load_fields_cached.cache_clear()
