import numpy as np
import pytest
from tests.node_tests._shared import make_field


def _make_node():
    from backend.nodes.periodic_translate import PeriodicTranslate
    return PeriodicTranslate()


def test_output_arity():
    node = _make_node()
    assert len(node.OUTPUTS) == 1
    assert node.OUTPUTS[0][0] == "DATA_FIELD"
    field = make_field()
    result = node.process(field, dx=1, dy=1, update_offsets=False)
    assert isinstance(result, tuple) and len(result) == 1


def test_translation_equals_numpy_roll():
    """A periodic translate by (dx, dy) is exactly np.roll(data, (dy, dx))."""
    node = _make_node()
    rng = np.random.default_rng(0)
    data = rng.standard_normal((32, 48))
    field = make_field(data=data)
    for dx, dy in [(3, 0), (0, -7), (5, -2), (-11, 4)]:
        (out,) = node.process(field, dx=dx, dy=dy, update_offsets=False)
        assert np.array_equal(out.data, np.roll(data, (dy, dx), axis=(0, 1))), (dx, dy)


def test_large_shifts_wrap_around():
    """Shifts larger than the field wrap around periodically."""
    node = _make_node()
    data = np.zeros((8, 8))
    data[0, 0] = 1.0
    field = make_field(data=data)
    (out,) = node.process(field, dx=9, dy=0, update_offsets=False)   # 9 == 1 mod 8
    assert out.data[0, 1] == 1.0
    assert out.data[0, 0] == 0.0


def test_pixel_leaving_field_reappears_on_opposite_side():
    node = _make_node()
    data = np.zeros((8, 8))
    data[0, 7] = 1.0
    field = make_field(data=data)
    # dx=-1 moves content left: the pixel at the last column lands in column 6
    (out,) = node.process(field, dx=-1, dy=0, update_offsets=False)
    assert out.data[0, 6] == 1.0
    assert out.data[0, 7] == 0.0
    # dy=1 moves content down: the top row lands on the second row
    data2 = np.zeros((8, 8))
    data2[0, 3] = 2.0
    (out2,) = node.process(make_field(data=data2), dx=0, dy=1, update_offsets=False)
    assert out2.data[1, 3] == 2.0
    assert out2.data[0, 3] == 0.0


def test_offsets_updated():
    """With update_offsets, shifting by +1 px moves the offset by -dx*dx_phys
    (wrapped into the [-real/2, real/2) range), so features keep their
    physical position."""
    node = _make_node()
    field = make_field(data=np.zeros((64, 64)), xreal=1e-6, yreal=2e-6)
    (out,) = node.process(field, dx=1, dy=0, update_offsets=True)
    d = 1e-6 / 64.0
    assert out.xoff == pytest.approx(-d, abs=1e-20)
    assert out.yoff == pytest.approx(0.0, abs=1e-20)
    (out2,) = node.process(field, dx=0, dy=2, update_offsets=True)
    d2 = 2e-6 / 64.0
    assert out2.xoff == pytest.approx(0.0, abs=1e-20)
    assert out2.yoff == pytest.approx(-2.0 * d2, abs=1e-20)


def test_offsets_preserved_when_not_updating():
    node = _make_node()
    field = make_field(data=np.zeros((16, 16)))
    field = field.replace(xoff=1.5e-8, yoff=-2.5e-8)
    (out,) = node.process(field, dx=3, dy=-2, update_offsets=False)
    assert out.xoff == field.xoff
    assert out.yoff == field.yoff


def test_metadata_preserved():
    node = _make_node()
    field = make_field(data=np.zeros((16, 16)), xreal=3e-6, yreal=2e-6)
    (out,) = node.process(field, dx=2, dy=2, update_offsets=True)
    assert out.xreal == field.xreal
    assert out.yreal == field.yreal
    assert out.si_unit_xy == field.si_unit_xy
    assert out.si_unit_z == field.si_unit_z
    assert out.data.shape == field.data.shape
    # Sum is preserved by the wrap (nothing is lost or created)
    assert out.data.sum() == pytest.approx(field.data.sum())
