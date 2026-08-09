import numpy as np
import pytest

from backend.data_types import LineData
from backend.node_registry import get_node_info
from tests.node_tests._shared import make_field


def test_good_mean_profile_single():
    from backend.nodes.good_mean_profile import GoodMeanProfile

    node = GoodMeanProfile()
    assert get_node_info("GoodMeanProfile")["category"] == "Level & Correct"
    assert len(node.OUTPUTS) == 2

    rows, cols = 64, 96
    rng = np.random.default_rng(11)
    x = np.linspace(-1.0, 1.0, cols)
    profile_true = 0.8 * np.sin(2.5 * np.pi * x) + 0.2 * x
    noise = rng.standard_normal((rows, cols)).astype(np.float64)
    data = profile_true[None, :] + noise
    # A few strong outliers outside the trimmed band.
    data[3, 17] += 5.0
    data[50, 71] -= 5.0
    field = make_field(data=data, xreal=4e-6, yreal=2e-6)

    corrected, profile = node.process(field, mode="single", trim_fraction=0.2)

    assert corrected.data.shape == field.data.shape
    assert np.isclose(corrected.data[3, 17], profile.data[17])
    assert np.isclose(corrected.data[50, 71], profile.data[71])
    # The good profile follows the underlying signal.
    assert np.corrcoef(profile.data, profile_true)[0, 1] > 0.94
    # Trimmed mean recovers the profile exactly for noisy data (trim_fraction
    # 0.2, yres 64 -> ntrim = 6 samples trimmed on each side).
    column_means = np.array([np.sort(data[:, j])[6:58].mean() for j in range(cols)])
    assert np.allclose(profile.data, column_means, atol=1e-9)

    assert isinstance(profile, LineData)
    assert profile.x_unit == field.si_unit_xy
    assert profile.y_unit == field.si_unit_z
    assert np.isclose(profile.x_axis[0], 0.0)
    assert np.isclose(profile.x_axis[-1], field.xreal)
    assert profile.x_axis.size == cols


def test_good_mean_profile_multiple():
    from backend.nodes.good_mean_profile import GoodMeanProfile

    node = GoodMeanProfile()

    rows, cols = 48, 64
    rng = np.random.default_rng(13)
    x = np.linspace(0.0, 1.0, cols)
    profile_true = 0.5 * np.sin(4.0 * np.pi * x)
    base = profile_true[None, :]
    d1 = base + rng.standard_normal((rows, cols)) * 0.05
    d2 = base + rng.standard_normal((rows, cols)) * 0.05
    # One pixel differs hugely between the scans: it must be rejected.
    d1[10, 20] += 3.0
    field_a = make_field(data=d1)
    field_b = make_field(data=d2)

    corrected, profile = node.process(field_a, mode="multiple", trim_fraction=0.05,
                                      second_field=field_b)

    assert corrected.data.shape == field_a.data.shape
    assert np.corrcoef(profile.data, profile_true)[0, 1] > 0.99
    # The outlier pixel was replaced by the good profile value of its column.
    assert np.isclose(corrected.data[10, 20], profile.data[20])
    # Identical scans give exactly the mean image.
    same_a = make_field(data=base + 0.25)
    same_b = make_field(data=base + 0.25)
    corrected2, profile2 = node.process(same_a, mode="multiple", trim_fraction=0.05,
                                        second_field=same_b)
    assert np.allclose(corrected2.data, base + 0.25)
    assert np.allclose(profile2.data, profile_true + 0.25)


def test_good_mean_profile_units():
    from backend.nodes.good_mean_profile import GoodMeanProfile

    node = GoodMeanProfile()
    field = make_field(data=np.random.default_rng(1).standard_normal((32, 48)),
                       xreal=3e-6, yreal=2e-6).replace(si_unit_z="nm")

    corrected, profile = node.process(field, mode="single", trim_fraction=0.1)
    assert corrected.si_unit_z == "nm"
    assert corrected.si_unit_xy == "m"
    assert corrected.xreal == field.xreal
    assert profile.y_unit == "nm"


def test_good_mean_profile_errors():
    from backend.nodes.good_mean_profile import GoodMeanProfile

    node = GoodMeanProfile()
    field = make_field()
    other = make_field(shape=(32, 64))

    with pytest.raises(ValueError, match="second field"):
        node.process(field, mode="multiple", trim_fraction=0.05)

    with pytest.raises(ValueError, match="shape"):
        node.process(field, mode="multiple", trim_fraction=0.05, second_field=other)

    with pytest.raises(ValueError, match="mode"):
        node.process(field, mode="bogus", trim_fraction=0.05)


def test_good_mean_profile_output_arity():
    from backend.nodes.good_mean_profile import GoodMeanProfile

    node = GoodMeanProfile()
    field = make_field()
    result = node.process(field, mode="single", trim_fraction=0.05)
    assert len(result) == 2
    assert isinstance(result[1], LineData)
