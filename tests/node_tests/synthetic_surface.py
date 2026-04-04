import numpy as np
import pytest


def test_all_patterns_produce_correct_shape():
    from backend.nodes.synthetic_surface import SyntheticSurface

    node = SyntheticSurface()
    for pattern in ("fbm", "white_noise", "lattice", "steps", "particles", "flat"):
        result, = node.process(
            pattern=pattern, xres=64, yres=48, xreal=1e-6, yreal=1e-6,
            amplitude=1e-9, seed=42,
        )
        assert result.data.shape == (48, 64), f"Failed for {pattern}"


def test_flat_is_zero():
    from backend.nodes.synthetic_surface import SyntheticSurface

    node = SyntheticSurface()
    result, = node.process(
        pattern="flat", xres=32, yres=32, xreal=1e-6, yreal=1e-6,
        amplitude=1e-9, seed=0,
    )
    assert np.allclose(result.data, 0.0)


def test_seed_reproducibility():
    from backend.nodes.synthetic_surface import SyntheticSurface

    node = SyntheticSurface()
    kwargs = dict(pattern="fbm", xres=32, yres=32, xreal=1e-6, yreal=1e-6,
                  amplitude=1e-9, seed=123)
    r1, = node.process(**kwargs)
    r2, = node.process(**kwargs)
    assert np.array_equal(r1.data, r2.data)


def test_amplitude_scaling():
    from backend.nodes.synthetic_surface import SyntheticSurface

    node = SyntheticSurface()
    result, = node.process(
        pattern="white_noise", xres=64, yres=64, xreal=1e-6, yreal=1e-6,
        amplitude=5e-9, seed=42,
    )
    assert result.data.max() <= 5e-9 + 1e-15
    assert result.data.min() >= -1e-15


def test_unknown_pattern():
    from backend.nodes.synthetic_surface import SyntheticSurface

    node = SyntheticSurface()
    with pytest.raises(ValueError):
        node.process(pattern="unknown", xres=32, yres=32, xreal=1e-6, yreal=1e-6,
                     amplitude=1e-9, seed=0)
