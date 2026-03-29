import numpy as np
from backend.data_types import DataField
from backend.node_registry import get_node_info
from tests.node_tests._shared import make_field


def test_angle_measure():
    from backend.nodes.angle_measure import AngleMeasure
    from backend.data_types import ImageData

    node = AngleMeasure()
    info = get_node_info("AngleMeasure")
    assert info["category"] == "Overlay"
    assert {entry["category"] for entry in info["menu_categories"]} == {"Overlay", "Measure"}
    required_inputs = AngleMeasure.INPUT_TYPES()["required"]
    optional_inputs = AngleMeasure.INPUT_TYPES().get("optional", {})
    assert required_inputs["input"][1]["accepted_types"] == ["DATA_FIELD", "IMAGE"]
    assert required_inputs["color"][1]["default"] == "#ff9800"
    assert required_inputs["stroke_width"][1]["default"] == 1.35
    assert optional_inputs["line_thickness"][1]["hidden"] is True
    assert optional_inputs["line_thickness_input"][1]["hidden"] is True

    field = make_field(data=np.zeros((32, 64), dtype=np.float64), xreal=4.0, yreal=2.0)
    output, table = node.process(
        field, color="#c62828", stroke_width=1.8,
        x1=0.2, y1=0.5, xm=0.5, ym=0.5, x2=0.5, y2=0.2, label_dx=0.0, label_dy=0.0,
    )
    rows = {row["quantity"]: row for row in table}
    assert isinstance(output, DataField)
    assert output is not field
    assert len(output.overlays) == len(field.overlays) + 1
    assert output.overlays[-1]["kind"] == "angle_measure"
    assert output.overlays[-1]["color"] == "#c62828"
    assert np.isclose(output.overlays[-1]["stroke_width"], 1.8)
    assert np.isclose(rows["Arm A length"]["value"], 1.2)
    assert np.isclose(rows["Arm B length"]["value"], 0.6)
    assert np.isclose(rows["Angle"]["value"], 90.0)
    assert rows["Angle"]["unit"] == "deg"
    assert rows["Vertex x"]["unit"] == field.si_unit_xy

    sanitized_output, _ = node.process(
        field, color="not-a-color", stroke_width=-0.7,
        x1=0.2, y1=0.5, xm=0.5, ym=0.5, x2=0.5, y2=0.2, label_dx=0.0, label_dy=0.0,
    )
    assert sanitized_output.overlays[-1]["color"] == "#ff9800"
    assert np.isclose(sanitized_output.overlays[-1]["stroke_width"], 0.35)

    image = np.zeros((50, 100, 3), dtype=np.uint8)
    image_output, image_table = node.process(
        image, color="#ff9800", stroke_width=1.25,
        x1=0.25, y1=0.5, xm=0.5, ym=0.5, x2=0.5, y2=0.25, label_dx=0.0, label_dy=0.0,
    )
    image_rows = {row["quantity"]: row for row in image_table}
    assert isinstance(image_output, ImageData)
    assert image_output.shape == image.shape
    assert np.count_nonzero(np.asarray(image_output)) > 0
    assert np.isclose(image_rows["Arm A length"]["value"], 24.75)
    assert np.isclose(image_rows["Arm B length"]["value"], 12.25)
    assert np.isclose(image_rows["Angle"]["value"], 90.0)
    assert image_rows["Arm A length"]["unit"] == "px"
