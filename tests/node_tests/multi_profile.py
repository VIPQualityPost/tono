import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_horizontal_center():
    from backend.nodes.multi_profile import MultipleProfiles

    node = MultipleProfiles()
    field = make_field(shape=(64, 128))
    (profile,) = node.process(field, field, row=-1, direction="horizontal", mode="overlay")
    assert len(profile.data) == 128, f"Expected width 128, got {len(profile.data)}"
    assert profile.x_axis is not None
    assert len(profile.x_axis) == len(profile.data)


def test_difference_mode():
    from backend.nodes.multi_profile import MultipleProfiles

    node = MultipleProfiles()
    data = np.random.default_rng(5).standard_normal((32, 32))
    field = make_field(data=data)
    (profile,) = node.process(field, field, row=-1, direction="horizontal", mode="difference")
    assert np.allclose(profile.data, 0.0), "Difference of same field should be zero"


def test_vertical_direction():
    from backend.nodes.multi_profile import MultipleProfiles

    node = MultipleProfiles()
    field = make_field(shape=(80, 40))
    (profile,) = node.process(field, field, row=-1, direction="vertical", mode="overlay")
    assert len(profile.data) == 80, f"Vertical profile length should be field height (80), got {len(profile.data)}"
