import numpy as np
from backend.data_types import DataField, ImageData
from backend.execution_context import active_node, execution_callbacks
from tests.node_tests._shared import make_field


def test_preview_image():
    from backend.nodes.preview_image import PreviewImage

    node = PreviewImage()
    preview_input = PreviewImage.INPUT_TYPES()["optional"]["input"]
    assert preview_input[0] == "ANNOTATION_SOURCE"
    assert preview_input[1]["accepted_types"] == ["DATA_FIELD", "IMAGE"]

    captured = []
    with execution_callbacks(preview=lambda nid, data_uri: captured.append(data_uri)), active_node("test"):
        field = make_field()
        node.preview(colormap="viridis", input=field)
        assert len(captured) == 1
        assert captured[0].startswith("data:image/png;base64,")

        captured.clear()
        field_with_overlay = field.replace(overlays=[{"kind": "annotation", "show_scale_bar": True, "show_color_map": False, "text_size": 14.0}])
        node.preview(colormap="viridis", input=field_with_overlay)
        assert len(captured) == 1
        assert captured[0].startswith("data:image/png;base64,")

        captured.clear()
        custom_colormap = {
            "mode": "custom",
            "stops": [
                {"position": 0.0, "color": "#000000"},
                {"position": 0.5, "color": "#ff0000"},
                {"position": 1.0, "color": "#ffffff"},
            ],
        }
        node.preview(colormap="auto", input=field, colormap_map=custom_colormap)
        assert len(captured) == 1
        assert captured[0].startswith("data:image/png;base64,")

        captured.clear()
        arr = np.random.default_rng(5).integers(0, 256, (32, 32), dtype=np.uint8)
        node.preview(colormap="gray", input=arr)
        assert len(captured) == 1

        captured.clear()
        node.preview(colormap="auto", input=field_with_overlay)
        assert len(captured) == 1
        assert captured[0].startswith("data:image/png;base64,")

        captured.clear()
        annotated_image = ImageData(
            np.zeros((24, 24, 3), dtype=np.uint8),
            metadata={"annotation_context": {"xreal": 1e-6, "si_unit_xy": "m"}},
        )
        node.preview(colormap="auto", input=annotated_image)
        assert len(captured) == 1
        assert captured[0].startswith("data:image/png;base64,")


def test_preview_no_input_raises():
    from backend.nodes.preview_image import PreviewImage
    node = PreviewImage()
    with execution_callbacks(preview=lambda nid, d: None), active_node("test"):
        try:
            node.preview(colormap="gray", input=None)
            assert False, "Expected ValueError"
        except ValueError:
            pass


def test_preview_invalid_type_raises():
    from backend.nodes.preview_image import PreviewImage
    node = PreviewImage()
    with execution_callbacks(preview=lambda nid, d: None), active_node("test"):
        try:
            node.preview(colormap="gray", input="not_an_image")
            assert False, "Expected TypeError"
        except TypeError:
            pass


def test_preview_float_grayscale():
    from backend.nodes.preview_image import PreviewImage
    node = PreviewImage()
    captured = []
    with execution_callbacks(preview=lambda nid, d: captured.append(d)), active_node("test"):
        # float32 2D array — covers the float normalization branch
        float_arr = np.random.default_rng(7).random((16, 16)).astype(np.float32)
        node.preview(colormap="viridis", input=float_arr)
        assert len(captured) == 1
        assert captured[0].startswith("data:image/png;base64,")

        captured.clear()
        # constant float array → normalized = zeros branch
        const_arr = np.ones((8, 8), dtype=np.float32)
        node.preview(colormap="viridis", input=const_arr)
        assert len(captured) == 1
