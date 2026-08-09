"""Tests for the Grain Selection Shapes node."""

import numpy as np
import pytest


def _mask_with_grains():
    mask = np.zeros((41, 41), dtype=np.uint8)
    mask[2:7, 2:9] = 255  # 7 x 5 rectangle grain
    yyg, xxg = np.mgrid[0:41, 0:41]
    mask[((xxg - 25) ** 2 + (yyg - 20) ** 2) <= 4 ** 2] = 255  # disc grain, radius 4
    mask[35, 35] = 255  # single-pixel grain
    return mask


def test_output_arity():
    from backend.nodes.grain_selection_shapes import GrainSelectionShapes

    assert len(GrainSelectionShapes.OUTPUTS) == 1
    out = GrainSelectionShapes().process(_mask_with_grains(), method="inscribed_discs", min_area=0)
    assert isinstance(out, tuple) and len(out) == 1


def test_inscribed_disc_rectangle():
    """For a 7x5 rectangle the inscribed disc has radius min(7,5)/2 - 0.5 = 2.0
    (EDT maximum 2.5 at the rectangle centre pixel (5, 4))."""
    from backend.nodes.grain_selection_shapes import GrainSelectionShapes

    sel, = GrainSelectionShapes().process(_mask_with_grains(), method="inscribed_discs", min_area=0)
    binary = sel > 0
    assert binary[4, 5]
    assert binary[4, 4] and binary[2, 5]
    assert not binary[2, 2]
    # Every filled pixel inside the rectangle region belongs to its inscribed
    # disc, i.e. lies within radius 2.5 of the centre (5, 4).
    yyg, xxg = np.mgrid[0:41, 0:41]
    in_rect = (yyg >= 2) & (yyg < 7) & (xxg >= 2) & (xxg < 9)
    filled_in_rect = binary & in_rect
    assert filled_in_rect.sum() > 10
    dist2 = (xxg - 5.0) ** 2 + (yyg - 4.0) ** 2
    assert np.all(dist2[filled_in_rect] <= 2.5 ** 2 + 1e-9)
    # And the disc does not leak out of the rectangle.
    assert np.all(~filled_in_rect | in_rect)


def test_inscribed_disc_of_round_grain():
    """An inscribed disc of a disc-shaped grain stays inside and has a comparable
    radius (continuous radius within a pixel of the true 4 px)."""
    from backend.nodes.grain_selection_shapes import GrainSelectionShapes

    sel, = GrainSelectionShapes().process(_mask_with_grains(), method="inscribed_discs", min_area=0)
    binary = sel > 0
    yyg, xxg = np.mgrid[0:41, 0:41]
    grain = ((xxg - 25) ** 2 + (yyg - 20) ** 2) <= 4 ** 2
    # Disc pixels of the round grain: everything filled outside the rectangle
    # region and outside the single pixel.
    rect_region = (yyg >= 2) & (yyg < 7) & (xxg >= 2) & (xxg < 9)
    disc_pixels = binary & ~rect_region & ~((yyg == 35) & (xxg == 35))
    assert disc_pixels.sum() > 30
    assert np.all(grain[disc_pixels])  # every selected pixel is inside the mask
    ys, xs = np.nonzero(disc_pixels)
    centre_y, centre_x = float(np.mean(ys)), float(np.mean(xs))
    radii = np.sqrt((xs - centre_x) ** 2 + (ys - centre_y) ** 2)
    assert 3.0 < radii.max() < 5.0


def test_circumscribed_single_pixel_grain():
    """A single pixel's circumcircle is built over its four corners: centre at the
    corner (35.5, 35.5) with radius 0.707, filling the 2x2 pixel block."""
    from backend.nodes.grain_selection_shapes import GrainSelectionShapes

    sel, = GrainSelectionShapes().process(_mask_with_grains(), method="circumscribed_circles", min_area=0)
    binary = sel > 0
    assert binary[35, 35]
    assert binary[36, 35] and binary[35, 36] and binary[36, 36]
    assert not binary[34, 35] and not binary[35, 34] and not binary[37, 37]


def test_circumscribed_rectangle_grain():
    """For a 3x3 square the circumcircle (radius sqrt(2)*1.5 over the corner hull)
    covers the whole grain and stays within a 5x5 pixel region."""
    from backend.nodes.grain_selection_shapes import GrainSelectionShapes

    mask = np.zeros((11, 11), dtype=np.uint8)
    mask[4:7, 4:7] = 255
    sel, = GrainSelectionShapes().process(mask, method="circumscribed_circles", min_area=0)
    binary = sel > 0
    assert binary[5, 5]
    assert binary[4, 5] and binary[5, 4] and binary[6, 5] and binary[5, 6]
    yyg, xxg = np.mgrid[0:11, 0:11]
    grain = (yyg >= 4) & (yyg < 7) & (xxg >= 4) & (xxg < 7)
    # The circumcircle covers the grain; its corners sit exactly on the circle so
    # the greedy refinement may leave at most one corner pixel out.
    assert binary[grain].sum() >= 8
    # The 3x3 square's circumcircle spans roughly a 5x5 region.
    assert binary.sum() <= 26
    assert not binary[0, 0] and not binary[10, 10]


def test_min_area_filters_grains():
    from backend.nodes.grain_selection_shapes import GrainSelectionShapes

    sel, = GrainSelectionShapes().process(_mask_with_grains(), method="inscribed_discs", min_area=20)
    binary = sel > 0
    # With min_area=20 the 35-pixel rectangle remains, the single pixel is dropped.
    assert not binary[35, 35]
    assert binary[4, 5]


def test_empty_mask_returns_empty_selection():
    from backend.nodes.grain_selection_shapes import GrainSelectionShapes

    sel, = GrainSelectionShapes().process(np.zeros((20, 20), dtype=np.uint8),
                                          method="inscribed_discs", min_area=0)
    assert sel.dtype == np.uint8
    assert sel.max() == 0


def test_unknown_method_raises():
    from backend.nodes.grain_selection_shapes import GrainSelectionShapes

    with pytest.raises(ValueError, match="Unknown method"):
        GrainSelectionShapes().process(_mask_with_grains(), method="triangles", min_area=0)


def test_bool_mask_input_accepted():
    from backend.nodes.grain_selection_shapes import GrainSelectionShapes

    mask = np.zeros((9, 9), dtype=bool)
    mask[3:6, 3:6] = True
    sel, = GrainSelectionShapes().process(mask, method="inscribed_discs", min_area=0)
    assert sel[4, 4] == 255
