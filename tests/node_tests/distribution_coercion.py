import numpy as np
from tests.node_tests._shared import make_field


def test_output_shape():
    from backend.nodes.distribution_coercion import DistributionCoercion

    node = DistributionCoercion()
    field = make_field(shape=(48, 64))

    for dist in ("uniform", "gaussian", "levels"):
        (result,) = node.process(field, distribution=dist, n_levels=4, processing="field")
        assert result.data.shape == field.data.shape


def test_uniform_distribution():
    from backend.nodes.distribution_coercion import DistributionCoercion

    node = DistributionCoercion()
    rng = np.random.default_rng(7)
    data = rng.exponential(scale=2.0, size=(64, 64))
    field = make_field(data=data)

    (result,) = node.process(field, distribution="uniform", n_levels=4, processing="field")

    assert np.isclose(result.data.min(), data.min())
    assert np.isclose(result.data.max(), data.max())

    # Histogram should be roughly uniform — check that no bin has more than
    # 2x the expected count.
    counts, _ = np.histogram(result.data.ravel(), bins=10)
    expected = result.data.size / 10
    assert all(c < 2.0 * expected for c in counts)


def test_levels_count():
    from backend.nodes.distribution_coercion import DistributionCoercion

    node = DistributionCoercion()
    field = make_field(shape=(64, 64))

    for n in (2, 5, 10):
        (result,) = node.process(field, distribution="levels", n_levels=n, processing="field")
        assert len(np.unique(result.data)) == n


def test_row_mode():
    from backend.nodes.distribution_coercion import DistributionCoercion

    node = DistributionCoercion()
    field = make_field(shape=(32, 48))

    (result,) = node.process(field, distribution="uniform", n_levels=4, processing="rows")
    assert result.data.shape == field.data.shape

    # Each row should span the row's own min/max
    for i in range(field.data.shape[0]):
        row_in = field.data[i]
        row_out = result.data[i]
        assert np.isclose(row_out.min(), row_in.min())
        assert np.isclose(row_out.max(), row_in.max())
