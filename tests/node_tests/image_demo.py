from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from backend.data_types import DataField
from backend.execution import ExecutionEngine
import backend.nodes  # noqa: F401

FIXTURES = Path(__file__).parent.parent / "fixtures"

pytestmark = pytest.mark.skipif(
    not (FIXTURES / "Bacteria.ibw").exists() or not (FIXTURES / "nanoparticles.npy").exists(),
    reason=(
        "tono-test-data fixtures not available — "
        "run `git submodule update --init tests/fixtures`"
    ),
)


def test_load_npy():
    from backend.nodes.image_demo import ImageDemo

    with patch("backend.nodes.image_demo.DEMO_DIR", FIXTURES):
        result = ImageDemo().load(name="nanoparticles.npy")

    # ImageDemo exposes only the data channels (no FILE_PATH prefix)
    assert len(result) == 1
    assert isinstance(result[0], DataField)
    assert result[0].data.ndim == 2


def test_load_ibw_multi_channel():
    from backend.nodes.image_demo import ImageDemo
    from backend.nodes.helpers import list_channels

    with patch("backend.nodes.image_demo.DEMO_DIR", FIXTURES):
        result = ImageDemo().load(name="Bacteria.ibw")

    fields = [v for v in result if isinstance(v, DataField)]
    # Every channel is exposed, in channel order.
    assert len(fields) == 4
    for field in fields:
        assert field.data.ndim == 2
    names = [entry["name"] for entry in list_channels(str(FIXTURES / "Bacteria.ibw"))]
    assert names == ["HeightTrace", "AmplitudeTrace", "PhaseTrace", "HeightTraceMod0"]
    # Slot k must carry channel k's data — the exact contract a shifted
    # output layout breaks.
    from backend.importers.ibw import load as ibw_load
    expected = ibw_load(FIXTURES / "Bacteria.ibw")
    for slot in range(len(fields)):
        assert np.allclose(fields[slot].data, expected[slot].data)


def test_load_not_found():
    from backend.nodes.image_demo import ImageDemo

    with patch("backend.nodes.image_demo.DEMO_DIR", FIXTURES):
        try:
            ImageDemo().load(name="nonexistent_file.png")
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass


def test_load_cache():
    from backend.nodes.image import Image
    from backend.nodes.image_demo import ImageDemo

    node = ImageDemo()
    Image._load_fields_cached.cache_clear()

    with patch("backend.nodes.image_demo.DEMO_DIR", FIXTURES):
        import backend.importers.array_image as _ai
        with patch.object(_ai, "load", wraps=_ai.load) as loader:
            (first,) = node.load(name="nanoparticles.npy")
            (second,) = node.load(name="nanoparticles.npy")
            assert loader.call_count == 1

        assert np.allclose(first.data, second.data)
        assert first is not second
        first.data[0, 0] = -999.0

        (third,) = node.load(name="nanoparticles.npy")
        assert third.data[0, 0] != -999.0

    Image._load_fields_cached.cache_clear()


def test_multi_layer_preview_payload():
    previews = []

    with patch("backend.nodes.image_demo.DEMO_DIR", FIXTURES):
        ExecutionEngine().execute(
            {"1": {"class_type": "ImageDemo", "inputs": {"name": "Bacteria.ibw", "colormap": "viridis"}}},
            on_preview=lambda node_id, payload: previews.append((node_id, payload)),
        )

    assert len(previews) == 1
    node_id, payload = previews[0]
    assert node_id == "1"
    assert payload["kind"] == "layer_gallery"
    # Bacteria has 4 channels; every channel gets a gallery layer.
    assert len(payload["layers"]) == 4
    assert all(isinstance(layer["name"], str) and layer["name"] for layer in payload["layers"])
    assert all(layer["image"].startswith("data:image/png;base64,") for layer in payload["layers"])
