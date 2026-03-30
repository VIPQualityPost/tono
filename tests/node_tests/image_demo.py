import os
from unittest.mock import patch

import numpy as np
from backend.data_types import DataField
from backend.execution import ExecutionEngine
import backend.nodes  # noqa: F401


def test_load_demo():
    from backend.nodes.image_demo import ImageDemo
    from backend.nodes.helpers import DEMO_DIR
    node = ImageDemo()

    result = node.load(name="nanoparticles.npy")
    # result[0] is the FILE_PATH string, fields follow
    assert len(result) >= 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], DataField)
    assert result[1].data.ndim == 2

    ibw_path = DEMO_DIR / "whiskers.ibw"
    if ibw_path.exists():
        result_ibw = node.load(name="whiskers.ibw")
        fields = [v for v in result_ibw if isinstance(v, DataField)]
        assert len(fields) == 4
        for field in fields:
            assert isinstance(field, DataField)

    try:
        node.load(name="nonexistent_file.png")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_load_demo_cache():
    from backend.nodes.image import Image
    from backend.nodes.image_demo import ImageDemo

    node = ImageDemo()
    Image._load_fields_cached.cache_clear()

    with patch.object(Image, "_load_image_or_array", wraps=Image._load_image_or_array) as loader:
        _, first = node.load(name="nanoparticles.npy")
        _, second = node.load(name="nanoparticles.npy")
        assert loader.call_count == 1

    assert np.allclose(first.data, second.data)
    assert first is not second
    first.data[0, 0] = -999.0

    _, third = node.load(name="nanoparticles.npy")
    assert third.data[0, 0] != -999.0

    Image._load_fields_cached.cache_clear()


def test_load_demo_multi_layer_preview_payload():
    from backend.nodes.helpers import DEMO_DIR
    ibw_path = DEMO_DIR / "whiskers.ibw"
    if not ibw_path.exists():
        return

    previews = []
    prompt = {
        "1": {
            "class_type": "ImageDemo",
            "inputs": {"name": "whiskers.ibw", "colormap": "viridis"},
        },
    }

    ExecutionEngine().execute(prompt, on_preview=lambda node_id, payload: previews.append((node_id, payload)))

    assert len(previews) == 1
    node_id, payload = previews[0]
    assert node_id == "1"
    assert payload["kind"] == "layer_gallery"
    assert len(payload["layers"]) == 4
    assert all(isinstance(layer["name"], str) and layer["name"] for layer in payload["layers"])
    assert all(layer["image"].startswith("data:image/png;base64,") for layer in payload["layers"])
