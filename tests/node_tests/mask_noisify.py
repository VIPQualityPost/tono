import numpy as np


def _make_test_mask():
    mask = np.zeros((64, 64), dtype=np.uint8)
    mask[20:40, 20:40] = 255
    return mask


def test_output_shape():
    from backend.nodes.mask_noisify import MaskNoisify
    node = MaskNoisify()
    mask = _make_test_mask()

    result, = node.process(mask, density=0.1, direction="both",
                           boundaries_only=True, seed=42)
    assert result.shape == mask.shape
    assert result.dtype == np.uint8


def test_zero_density_unchanged():
    from backend.nodes.mask_noisify import MaskNoisify
    node = MaskNoisify()
    mask = _make_test_mask()

    result, = node.process(mask, density=0.0, direction="both",
                           boundaries_only=True, seed=42)
    assert np.array_equal(result, mask)


def test_density_modifies_mask():
    from backend.nodes.mask_noisify import MaskNoisify
    node = MaskNoisify()
    mask = _make_test_mask()

    result, = node.process(mask, density=0.5, direction="both",
                           boundaries_only=True, seed=42)
    assert not np.array_equal(result, mask)


def test_seed_reproducibility():
    from backend.nodes.mask_noisify import MaskNoisify
    node = MaskNoisify()
    mask = _make_test_mask()

    result_a, = node.process(mask, density=0.3, direction="both",
                             boundaries_only=True, seed=123)
    result_b, = node.process(mask, density=0.3, direction="both",
                             boundaries_only=True, seed=123)
    assert np.array_equal(result_a, result_b)
