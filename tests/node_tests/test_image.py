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
        assert len(result) == 1
        field = result[0]
        assert field.data.shape == (48, 64)
        assert field.data.dtype == np.float64

        arr_rgb = np.random.default_rng(2).integers(0, 256, (32, 32, 3), dtype=np.uint8)
        img_rgb = PILImage.fromarray(arr_rgb, mode="RGB")
        path_rgb = os.path.join(tmpdir, "test_rgb.png")
        img_rgb.save(path_rgb)

        result_rgb = node.load(filename=path_rgb)
        assert len(result_rgb) == 1
        assert result_rgb[0].data.shape == (32, 32)

        data_npy = np.random.default_rng(3).standard_normal((50, 60))
        path_npy = os.path.join(tmpdir, "test.npy")
        np.save(path_npy, data_npy)

        result_npy = node.load(filename=path_npy)
        assert np.allclose(result_npy[0].data, data_npy)

        custom_colormap = {
            "mode": "custom",
            "stops": [
                {"position": 0.0, "color": "#000000"},
                {"position": 0.5, "color": "#ff0000"},
                {"position": 1.0, "color": "#ffffff"},
            ],
        }
        result_custom = node.load(filename=path, colormap_map=custom_colormap)
        assert isinstance(result_custom[0].colormap, dict)
        assert result_custom[0].colormap["mode"] == "custom"
        assert len(result_custom[0].colormap["stops"]) == 3

        result_from_path = node.load(filename="", path=path)
        assert len(result_from_path) == 1
        assert result_from_path[0].data.shape == (48, 64)


def test_load_file_npz():
    from backend.nodes.image import Image
    node = Image()
    with tempfile.TemporaryDirectory() as tmpdir:
        data = np.random.default_rng(99).standard_normal((30, 40))
        path = os.path.join(tmpdir, "test.npz")
        np.savez(path, my_array=data)

        result = node.load(filename=path)
        assert len(result) == 1
        assert np.allclose(result[0].data, data)


def test_load_file_cache():
    from backend.nodes.image import Image
    node = Image()
    Image._load_fields_cached.cache_clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        data = np.arange(16, dtype=np.float64).reshape(4, 4)
        path = os.path.join(tmpdir, "cached.npy")
        np.save(path, data)

        with patch.object(Image, "_load_image_or_array", wraps=Image._load_image_or_array) as loader:
            first, = node.load(filename=path)
            second, = node.load(filename=path)
            assert loader.call_count == 1

        assert np.allclose(first.data, data)
        assert np.allclose(second.data, data)
        assert first is not second
        first.data[0, 0] = -999.0

        third, = node.load(filename=path)
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
    node = ImageNode()
    warnings = []
    ImageNode._broadcast_warning_fn = lambda nid, msg: warnings.append(msg)
    ImageNode._current_node_id = "test"

    with tempfile.TemporaryDirectory() as tmpdir:
        arr = np.random.default_rng(10).integers(0, 256, (16, 16), dtype=np.uint8)
        img = PILImage.fromarray(arr)
        path = os.path.join(tmpdir, "test.png")
        img.save(path)

        result = node.load(filename=path)
        assert len(result) == 1
        assert len(warnings) == 1
        assert "Uncalibrated" in warnings[0]

    ImageNode._broadcast_warning_fn = None


def test_load_file_ibw():
    from backend.nodes.image import Image
    node = Image()
    ibw_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "demo", "BR_New20012.ibw"))
    if not os.path.exists(ibw_path):
        return

    result = node.load(filename=ibw_path)
    assert len(result) == 4

    for i, field in enumerate(result):
        assert isinstance(field, DataField)
        assert field.data.shape == (512, 1024)
        assert field.data.dtype == np.float64
        assert field.xreal > 1e-8
        assert field.yreal > 1e-8
        assert field.si_unit_xy == "m"
        assert field.si_unit_z == "m"

    assert result[0].xreal == result[1].xreal
    assert result[0].yreal == result[1].yreal
    assert not np.array_equal(result[0].data, result[1].data)
