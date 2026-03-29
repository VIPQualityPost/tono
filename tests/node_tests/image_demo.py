import os
from unittest.mock import patch

import numpy as np
from backend.data_types import DataField
from backend.execution import ExecutionEngine
import backend.nodes  # noqa: F401


def test_load_demo():
    from backend.nodes.image_demo import ImageDemo
    node = ImageDemo()

    result = node.load(name="nanoparticles.npy")
    assert len(result) >= 1
    assert isinstance(result[0], DataField)
    assert result[0].data.ndim == 2

    result_ibw = node.load(name="whiskers.ibw")
    assert len(result_ibw) == 4
    for field in result_ibw:
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
        first, = node.load(name="nanoparticles.npy")
        second, = node.load(name="nanoparticles.npy")
        assert loader.call_count == 1

    assert np.allclose(first.data, second.data)
    assert first is not second
    first.data[0, 0] = -999.0

    third, = node.load(name="nanoparticles.npy")
    assert third.data[0, 0] != -999.0

    Image._load_fields_cached.cache_clear()


def test_load_demo_multi_layer_preview_payload():
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
