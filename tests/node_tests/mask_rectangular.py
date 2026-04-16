import numpy as np

from tests.node_tests._shared import make_field


def test_mask_rectangular_basic():
    from backend.nodes.mask_rectangular import RectangularMask

    node = RectangularMask()
    field = make_field(data=np.zeros((32, 32)))

    mask, = node.process(
        field, x1=0.25, y1=0.25, x2=0.75, y2=0.75, square=False, invert=False,
    )
    assert mask.dtype == np.uint8
    assert mask.shape == (32, 32)
    # Corners defined by 0.25..0.75 on a 32-wide field → pixels 8..24
    assert mask[0, 0] == 0
    assert mask[16, 16] == 255
    assert np.all(mask[8:24, 8:24] == 255)
    assert np.all(mask[:8, :] == 0)
    assert np.all(mask[24:, :] == 0)


def test_mask_rectangular_invert():
    from backend.nodes.mask_rectangular import RectangularMask

    node = RectangularMask()
    field = make_field(data=np.zeros((32, 32)))

    mask, = node.process(
        field, x1=0.25, y1=0.25, x2=0.75, y2=0.75, square=False, invert=True,
    )
    assert mask[0, 0] == 255
    assert mask[16, 16] == 0


def test_mask_rectangular_corner_inputs_override_widgets():
    from backend.nodes.mask_rectangular import RectangularMask

    node = RectangularMask()
    field = make_field(data=np.zeros((32, 32)))

    mask, = node.process(
        field, x1=0.0, y1=0.0, x2=1.0, y2=1.0, square=False, invert=False,
        corner_a=(0.5, 0.5), corner_b=(1.0, 1.0),
    )
    # Corner override → rectangle is the lower-right quadrant (pixels 16..32)
    assert mask[0, 0] == 0
    assert mask[24, 24] == 255
    assert np.all(mask[16:32, 16:32] == 255)
    assert np.all(mask[:16, :16] == 0)


def test_mask_rectangular_reversed_corners():
    """x2 < x1 or y2 < y1 should still produce the same rectangle."""
    from backend.nodes.mask_rectangular import RectangularMask

    node = RectangularMask()
    field = make_field(data=np.zeros((32, 32)))

    forward, = node.process(
        field, x1=0.25, y1=0.25, x2=0.75, y2=0.75, square=False, invert=False,
    )
    reversed_, = node.process(
        field, x1=0.75, y1=0.75, x2=0.25, y2=0.25, square=False, invert=False,
    )
    assert np.array_equal(forward, reversed_)


def test_mask_rectangular_clamps_out_of_bounds():
    from backend.nodes.mask_rectangular import RectangularMask

    node = RectangularMask()
    field = make_field(data=np.zeros((16, 16)))

    mask, = node.process(
        field, x1=-0.5, y1=-0.5, x2=2.0, y2=2.0, square=False, invert=False,
    )
    assert mask.shape == (16, 16)
    assert np.all(mask == 255)


def test_mask_rectangular_square_shrinks_longer_side():
    """With square=True on a square field, the longer side collapses to the shorter."""
    from backend.nodes.mask_rectangular import RectangularMask

    node = RectangularMask()
    field = make_field(data=np.zeros((64, 64)))

    # Non-square fractional region: 0.1..0.9 in x (80% wide), 0.1..0.5 in y (40% tall).
    # With square=True the shorter dimension (y, 40%) wins; x shrinks to match.
    mask, = node.process(
        field, x1=0.1, y1=0.1, x2=0.9, y2=0.5, square=True, invert=False,
    )
    ys, xs = np.where(mask == 255)
    assert ys.size > 0
    width = xs.max() - xs.min() + 1
    height = ys.max() - ys.min() + 1
    assert width == height, f"expected square, got {width}x{height}"


def test_mask_rectangular_square_physical_aspect():
    """On a field with non-square physical aspect, 'square' is physical, not pixel."""
    from backend.nodes.mask_rectangular import RectangularMask

    node = RectangularMask()
    # xreal = 2e-6, yreal = 1e-6 — so a physical square covers twice the x-fraction of the y-fraction.
    field = make_field(data=np.zeros((64, 64)), xreal=2e-6, yreal=1e-6)

    # Start with a region 0.1..0.9 in x (0.8 frac, 1.6e-6 phys) and 0.1..0.9 in y (0.8 frac, 0.8e-6 phys).
    # Shorter physical side = 0.8e-6. In x that's 0.4 fraction → shrink x to 0.1..0.5.
    mask, = node.process(
        field, x1=0.1, y1=0.1, x2=0.9, y2=0.9, square=True, invert=False,
    )
    ys, xs = np.where(mask == 255)
    assert ys.size > 0
    # The selected region in pixels should be roughly 0.1..0.5 in x (pixels ~6..32)
    # and 0.1..0.9 in y (pixels ~6..58)
    assert xs.max() < 40
    assert ys.max() > 50


def test_mask_rectangular_emits_overlay():
    from backend.execution_context import active_node, execution_callbacks
    from backend.nodes.mask_rectangular import RectangularMask

    node = RectangularMask()
    field = make_field(data=np.zeros((32, 32)))

    overlays = []
    with execution_callbacks(
        overlay=lambda nid, d: overlays.append(d),
    ), active_node("test"):
        node.process(
            field, x1=0.1, y1=0.1, x2=0.9, y2=0.9, square=False, invert=False,
        )

    assert len(overlays) == 1
    assert overlays[0]["kind"] == "crop_box"
    assert overlays[0]["section_title"] == "Preview"
    assert overlays[0]["x1"] == 0.1
    assert overlays[0]["image"].startswith("data:image/png;base64,")
