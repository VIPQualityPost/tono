import numpy as np
from backend.data_types import DataField
from backend.execution_context import execution_callbacks, active_node


def test_crop_resize_field():
    from backend.nodes.crop_resize import CropResizeField
    node = CropResizeField()

    data = np.arange(32, dtype=np.float64).reshape(4, 8)
    field = DataField(
        data=data,
        xreal=8.0,
        yreal=4.0,
        xoff=10.0,
        yoff=20.0,
        si_unit_xy="nm",
        si_unit_z="nm",
        overlays=[{"kind": "markup", "shapes": [{"kind": "line", "x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9, "width": 2, "color": "#ffffff"}]}],
    )

    overlays = []
    with execution_callbacks(overlay=lambda nid, data: overlays.append(data)), active_node("test"):
        cropped, = node.process(field, x1=0.25, y1=0.25, x2=0.75, y2=1.0, target_width=0, target_height=0, interpolation="bilinear")
        assert cropped.data.shape == (3, 4)
        assert np.array_equal(cropped.data, data[1:4, 2:6])
        assert cropped.xreal == 4.0
        assert cropped.yreal == 3.0
        assert cropped.xoff == 12.0
        assert cropped.yoff == 21.0
        assert cropped.si_unit_xy == field.si_unit_xy
        assert cropped.si_unit_z == field.si_unit_z
        assert cropped.overlays == []
        assert len(overlays) == 1
        assert overlays[0]["kind"] == "crop_box"
        assert overlays[0]["image"].startswith("data:image/png;base64,")
        assert overlays[0]["a_locked"] is False
        assert overlays[0]["b_locked"] is False

        resized, = node.process(field, x1=0.0, y1=0.0, x2=1.0, y2=1.0, target_width=8, target_height=0, interpolation="bilinear", corner_a=(0.25, 0.25), corner_b=(0.75, 1.0))
        assert resized.data.shape == (6, 8)
        assert resized.xreal == cropped.xreal
        assert resized.yreal == cropped.yreal
        assert resized.xoff == cropped.xoff
        assert resized.yoff == cropped.yoff
        assert resized.domain == field.domain
        assert overlays[-1]["a_locked"] is True
        assert overlays[-1]["b_locked"] is True

        reversed_crop, = node.process(field, x1=0.75, y1=1.0, x2=0.25, y2=0.25, target_width=0, target_height=0, interpolation="nearest")
        assert np.array_equal(reversed_crop.data, cropped.data)

        try:
            node.process(field, x1=0.9, y1=0.0, x2=0.9, y2=1.0, target_width=0, target_height=0, interpolation="nearest")
            raise AssertionError("Expected invalid crop bounds to raise ValueError")
        except ValueError:
            pass


def test_crop_resize_square_constraint():
    """With square=True, the crop region is coerced to a physical square."""
    from backend.nodes.crop_resize import CropResizeField
    node = CropResizeField()

    # Square-pixel field (xreal == yreal): fraction-square == physical-square.
    data = np.arange(64 * 64, dtype=np.float64).reshape(64, 64)
    field = DataField(
        data=data, xreal=1e-6, yreal=1e-6,
        si_unit_xy="m", si_unit_z="m",
    )

    # Requested region: 0.1..0.9 (wide, 80%) x 0.1..0.5 (tall, 40%).
    # Physical-square clamp shrinks the longer (x) side to match y → 40% x 40%.
    cropped, = node.process(
        field, x1=0.1, y1=0.1, x2=0.9, y2=0.5,
        target_width=0, target_height=0, interpolation="bilinear", square=True,
    )
    assert cropped.data.shape[0] == cropped.data.shape[1], (
        f"expected square crop, got {cropped.data.shape}"
    )
    assert np.isclose(cropped.xreal, cropped.yreal)


def test_crop_resize_square_physical_aspect():
    """Square on a non-square-pixel field gives a physical square (not pixel square)."""
    from backend.nodes.crop_resize import CropResizeField
    node = CropResizeField()

    # 64x64 pixels but xreal = 2*yreal → x is physically twice as wide per fraction.
    data = np.arange(64 * 64, dtype=np.float64).reshape(64, 64)
    field = DataField(
        data=data, xreal=2e-6, yreal=1e-6,
        si_unit_xy="m", si_unit_z="m",
    )

    # Requested region: 0.1..0.9 x 0.1..0.9 (both 80% fraction).
    # Physical widths: 0.8 * 2e-6 = 1.6e-6 vs 0.8 * 1e-6 = 0.8e-6.
    # Shorter is y (0.8e-6). Clamp x to 0.4 fraction → 0.1..0.5.
    cropped, = node.process(
        field, x1=0.1, y1=0.1, x2=0.9, y2=0.9,
        target_width=0, target_height=0, interpolation="bilinear", square=True,
    )
    assert np.isclose(cropped.xreal, cropped.yreal, rtol=0.05), (
        f"expected physical square, got xreal={cropped.xreal} yreal={cropped.yreal}"
    )


def test_crop_resize_overlay_includes_aspect():
    """Overlay payload should include xreal/yreal so the frontend can snap to square."""
    from backend.nodes.crop_resize import CropResizeField
    node = CropResizeField()

    data = np.ones((16, 16), dtype=np.float64)
    field = DataField(
        data=data, xreal=3e-6, yreal=2e-6,
        si_unit_xy="m", si_unit_z="m",
    )

    overlays = []
    with execution_callbacks(overlay=lambda nid, d: overlays.append(d)), active_node("test"):
        node.process(
            field, x1=0.1, y1=0.1, x2=0.9, y2=0.9,
            target_width=0, target_height=0, interpolation="bilinear",
        )

    assert overlays[0]["xreal"] == 3e-6
    assert overlays[0]["yreal"] == 2e-6
