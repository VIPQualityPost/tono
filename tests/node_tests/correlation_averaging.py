import numpy as np
import pytest
from tests.node_tests._shared import make_field


def _repeat_field(size=64, period=10, patch_size=5, noise=0.05, x0=4, y0=4, seed=7):
    """Field with a small Gaussian-like patch repeated on a grid, plus noise.

    The template (first repeat) occupies rows y0:y0+patch_size,
    cols x0:x0+patch_size; repeats are spaced by *period* pixels.
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:patch_size, 0:patch_size]
    patch = 20.0 * np.exp(-((xx - patch_size / 2) ** 2 + (yy - patch_size / 2) ** 2) / 2.0)
    data = np.zeros((size, size))
    for r in range(y0, size - patch_size + 1, period):
        for c in range(x0, size - patch_size + 1, period):
            data[r:r + patch_size, c:c + patch_size] += patch
    return data + noise * rng.standard_normal((size, size)), patch


def _template_rect(field, x0_px=4, y0_px=4, size_px=5):
    """Physical rectangle of the first repeat.

    Fields in these tests use dyadic-exact extents (xreal=yreal=2**-16, 64 px)
    so that the node's truncating pixel conversion (rtoj) is exact: 4 px -> 4,
    9 px -> 9, keeping the template exactly size_px pixels.
    """
    return {
        "x": x0_px * field.dx,
        "y": y0_px * field.dy,
        "width": size_px * field.dx,
        "height": size_px * field.dy,
    }


def test_correlation_averaging_output_arity_and_schema():
    from backend.nodes.correlation_averaging import CorrelationAveraging

    data, _ = _repeat_field()
    field = make_field(data=data, xreal=2.0**-16, yreal=2.0**-16)
    node = CorrelationAveraging()
    result, alignment = node.process(field, **_template_rect(field))
    assert len((result, alignment)) == len(node.OUTPUTS) == 2
    assert result.data.shape == field.data.shape
    assert len(alignment) > 0
    for row in alignment:
        assert {"quantity", "value", "unit"} <= set(row.keys())


def test_correlation_averaging_score_matches_gwyddion():
    """_normalized_correlation_score reproduces GWY_CORRELATION_NORMAL exactly,
    including the -1 fill outside the valid region (brute-force port of the C)."""
    from backend.nodes.correlation_averaging import _normalized_correlation_score

    rng = np.random.default_rng(11)
    data = rng.standard_normal((11, 13))
    for kernel_shape in [(5, 5), (4, 3), (3, 6)]:  # odd and even sizes
        ky, kx = kernel_shape
        kernel = rng.standard_normal(kernel_shape)
        xoff, yoff = (kx - 1) // 2, (ky - 1) // 2
        kavg = kernel.mean()
        krms = float(np.sqrt(np.mean((kernel - kavg) ** 2)))

        expected = np.full(data.shape, -1.0)
        for i in range(yoff, data.shape[0] - ky + yoff + 1):
            for j in range(xoff, data.shape[1] - kx + xoff + 1):
                win = data[i - yoff:i - yoff + ky, j - xoff:j - xoff + kx]
                davg = win.mean()
                drms = float(np.sqrt(np.mean((win - davg) ** 2)))
                if krms == 0.0 or drms == 0.0:
                    expected[i, j] = 0.0
                    continue
                s = float(np.mean((win - davg) * (kernel - kavg)))
                expected[i, j] = s / (drms * krms)

        got = _normalized_correlation_score(data, kernel)
        assert np.allclose(got, expected, atol=1e-12)


def test_correlation_averaging_reduces_noise_at_repeats():
    """Repeats are located by the smoothed correlation score and replaced by the
    noise-averaged patch, reducing RMS deviation from the clean template."""
    from backend.nodes.correlation_averaging import CorrelationAveraging

    data, patch = _repeat_field()
    field = make_field(data=data, xreal=2.0**-16, yreal=2.0**-16)
    node = CorrelationAveraging()
    result, alignment = node.process(field, **_template_rect(field))

    # template (first repeat) patch after averaging, and another repeat at (14, 14)
    for top, left in [(4, 4), (14, 14)]:
        averaged = result.data[top:top + 5, left:left + 5]
        original = data[top:top + 5, left:left + 5]
        assert np.sqrt(np.mean((averaged - patch) ** 2)) < np.sqrt(np.mean((original - patch) ** 2))


def test_correlation_averaging_alignment_rows():
    """Detected repeats sit on the grid: offsets are multiples of the period
    (within one pixel) and the template itself reports (0, 0)."""
    from backend.nodes.correlation_averaging import CorrelationAveraging

    data, patch = _repeat_field(noise=0.02)
    field = make_field(data=data, xreal=2.0**-16, yreal=2.0**-16)
    node = CorrelationAveraging()
    result, alignment = node.process(field, **_template_rect(field))
    x_off = [row["value"] for row in alignment if row["quantity"].endswith("X offset")]
    y_off = [row["value"] for row in alignment if row["quantity"].endswith("Y offset")]
    assert len(x_off) >= 5  # several repeats found
    assert any(abs(v) < 0.5 for v in x_off) and any(abs(v) < 0.5 for v in y_off)
    for vx, vy in zip(x_off, y_off):
        # grid-aligned: at most 1 px deviation from an exact multiple of the period
        assert abs(vx - round(vx / 10.0) * 10.0) <= 1.0
        assert abs(vy - round(vy / 10.0) * 10.0) <= 1.0


def test_correlation_averaging_preserves_metadata():
    from backend.nodes.correlation_averaging import CorrelationAveraging

    data, _ = _repeat_field()
    field = make_field(data=data, xreal=2e-6, yreal=3e-6)
    node = CorrelationAveraging()
    result, alignment = node.process(field, **_template_rect(field))
    assert result.si_unit_z == field.si_unit_z == "m"
    assert result.si_unit_xy == field.si_unit_xy == "m"
    assert result.xreal == 2e-6 and result.yreal == 3e-6
    assert np.shares_memory(result.data, data) is False


def test_correlation_averaging_errors():
    from backend.nodes.correlation_averaging import CorrelationAveraging

    field = make_field()
    node = CorrelationAveraging()
    # template outside the field
    with pytest.raises(ValueError):
        node.process(field, x=0.9, y=0.9, width=0.2, height=0.2)
    # collapsed template
    with pytest.raises(ValueError):
        node.process(field, x=0.0, y=0.0, width=1e-15, height=1e-15)
    # template larger than the field
    with pytest.raises(ValueError):
        node.process(field, x=0.0, y=0.0, width=10.0, height=10.0)
