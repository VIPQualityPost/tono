import numpy as np
from backend.data_types import DataField


def test_flip_field():
    from backend.nodes.flip import FlipField
    from backend.node_registry import get_node_info

    node = FlipField()
    data = np.arange(1, 10, dtype=np.float64).reshape(3, 3)
    markup_overlay = {
        "kind": "markup",
        "shapes": [
            {"kind": "line", "x1": 0.1, "y1": 0.2, "x2": 0.9, "y2": 0.8, "width": 2, "color": "#ffffff"},
            {"kind": "rectangle", "x1": 0.15, "y1": 0.1, "x2": 0.45, "y2": 0.6, "width": 3, "color": "#ff0000"},
        ],
    }
    annotation_overlay = {"kind": "annotation", "show_scale_bar": True, "show_color_map": False, "text_size": 14.0}
    field = DataField(data=data, xreal=3.0, yreal=4.0, xoff=10.0, yoff=20.0, si_unit_xy="nm", si_unit_z="nm", overlays=[markup_overlay, annotation_overlay])

    assert get_node_info("FlipField")["category"] == "Geometry"

    flipped_x, = node.process(field, axis="x")
    assert np.array_equal(flipped_x.data, np.flipud(data))
    assert flipped_x.xreal == field.xreal
    assert flipped_x.yreal == field.yreal
    assert flipped_x.xoff == field.xoff
    assert flipped_x.yoff == field.yoff
    assert np.isclose(flipped_x.overlays[0]["shapes"][0]["x1"], 0.1)
    assert np.isclose(flipped_x.overlays[0]["shapes"][0]["y1"], 0.8)
    assert np.isclose(flipped_x.overlays[0]["shapes"][0]["x2"], 0.9)
    assert np.isclose(flipped_x.overlays[0]["shapes"][0]["y2"], 0.2)
    assert np.isclose(flipped_x.overlays[0]["shapes"][1]["x1"], 0.15)
    assert np.isclose(flipped_x.overlays[0]["shapes"][1]["y1"], 0.4)
    assert np.isclose(flipped_x.overlays[0]["shapes"][1]["x2"], 0.45)
    assert np.isclose(flipped_x.overlays[0]["shapes"][1]["y2"], 0.9)
    assert flipped_x.overlays[1] == annotation_overlay

    flipped_y, = node.process(field, axis="y")
    assert np.array_equal(flipped_y.data, np.fliplr(data))
    assert np.isclose(flipped_y.overlays[0]["shapes"][0]["x1"], 0.9)
    assert np.isclose(flipped_y.overlays[0]["shapes"][0]["y1"], 0.2)
    assert np.isclose(flipped_y.overlays[0]["shapes"][0]["x2"], 0.1)
    assert np.isclose(flipped_y.overlays[0]["shapes"][0]["y2"], 0.8)

    assert field.overlays[0]["shapes"][0]["x1"] == markup_overlay["shapes"][0]["x1"]

    try:
        node.process(field, axis="diagonal")
        raise AssertionError("Expected invalid flip axis to raise ValueError")
    except ValueError:
        pass

    # _flip_overlays with non-list input → returns []
    assert FlipField._flip_overlays(None, "x") == []
    assert FlipField._flip_overlays("not_a_list", "y") == []

    # Non-dict item in overlays → skipped
    field_bad_overlay = DataField(data=data, overlays=["not_a_dict", markup_overlay])
    flipped_bad, = node.process(field_bad_overlay, axis="x")
    assert len(flipped_bad.overlays) == 1

    # Shape with None coordinates → returns shape unchanged
    shape_no_coords = {"kind": "line", "x1": None, "y1": None, "x2": None, "y2": None}
    overlay_no_coords = {"kind": "markup", "shapes": [shape_no_coords]}
    field_no_coords = DataField(data=data, overlays=[overlay_no_coords])
    flipped_nc, = node.process(field_no_coords, axis="x")
    assert len(flipped_nc.overlays) == 1
