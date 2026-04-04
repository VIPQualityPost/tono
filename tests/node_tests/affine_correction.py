import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_identity_transform():
    """No shear, unit scale, zero rotation should return near-identical data."""
    from backend.nodes.affine_correction import AffineCorrection

    node = AffineCorrection()
    field = make_field(shape=(32, 32))
    result, = node.process(field, shear_x=0.0, shear_y=0.0, scale_x=1.0, scale_y=1.0, angle=0.0)
    assert result.data.shape == (32, 32)
    assert np.allclose(result.data, field.data, atol=1e-10)


def test_scale_changes_values():
    from backend.nodes.affine_correction import AffineCorrection

    node = AffineCorrection()
    field = make_field(shape=(32, 32))
    result, = node.process(field, shear_x=0.0, shear_y=0.0, scale_x=2.0, scale_y=1.0, angle=0.0)
    assert result.data.shape == (32, 32)
    # Scaled field should differ from original
    assert not np.allclose(result.data, field.data)


def test_rotation_preserves_shape():
    from backend.nodes.affine_correction import AffineCorrection

    node = AffineCorrection()
    field = make_field(shape=(48, 64))
    result, = node.process(field, shear_x=0.0, shear_y=0.0, scale_x=1.0, scale_y=1.0, angle=10.0)
    assert result.data.shape == (48, 64)


def test_shear_changes_values():
    from backend.nodes.affine_correction import AffineCorrection

    node = AffineCorrection()
    # Use a non-symmetric field so shear has a visible effect
    data = np.outer(np.arange(32), np.ones(32))
    field = make_field(data=data)
    result, = node.process(field, shear_x=0.3, shear_y=0.0, scale_x=1.0, scale_y=1.0, angle=0.0)
    assert not np.allclose(result.data, field.data)
