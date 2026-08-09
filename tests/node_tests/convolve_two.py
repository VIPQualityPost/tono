import numpy as np
import pytest
from scipy.signal import convolve2d
from tests.node_tests._shared import make_field


def test_convolve_output_arity():
    from backend.nodes.convolve_two import ConvolveTwoImages

    field = make_field(data=np.random.default_rng(0).standard_normal((32, 32)))
    kernel = make_field(data=np.ones((3, 3)))
    node = ConvolveTwoImages()
    result = node.process(field, kernel, mode="same")
    assert len(result) == len(node.OUTPUTS) == 1


def test_convolve_same_matches_scipy():
    """'same' mode equals scipy convolve2d for odd kernels (their centres agree
    with the node's centre at kx//2)."""
    from backend.nodes.convolve_two import ConvolveTwoImages

    rng = np.random.default_rng(4)
    a = rng.standard_normal((24, 20))
    b = rng.standard_normal((5, 3))  # odd x/y sizes
    node = ConvolveTwoImages()
    (out,) = node.process(make_field(data=a), make_field(data=b), mode="same")
    expected = convolve2d(a, b, mode="same")
    assert np.allclose(out.data, expected, rtol=1e-10, atol=1e-12)
    assert out.data.shape == a.shape


def test_convolve_same_even_kernel_centre():
    """Even kernels use the kx//2 center convention, not scipy's
    (kx//2 - 1): the node output equals the zero-exterior full convolution
    sliced at (ky//2, kx//2), which scipy's 'same' mode does not reproduce."""
    from backend.nodes.convolve_two import ConvolveTwoImages

    rng = np.random.default_rng(9)
    a = rng.standard_normal((16, 14))
    b = rng.standard_normal((4, 6))
    na, ma = a.shape
    ky, kx = b.shape
    # out[j,i] = sum_{k,l} b[k,l] * a_ext[j + ky//2 - k, i + kx//2 - l]
    # with a_ext the zero-exterior extension of a (data at rows [ky, ky+na)).
    a_ext = np.pad(a, ((ky, ky), (kx, kx)), constant_values=0.0)
    expected = np.zeros((na, ma))
    for j in range(na):
        for i in range(ma):
            s = 0.0
            for k in range(ky):
                for l in range(kx):
                    s += b[k, l] * a_ext[j + ky // 2 - k + ky, i + kx // 2 - l + kx]
            expected[j, i] = s

    node = ConvolveTwoImages()
    (out,) = node.process(make_field(data=a), make_field(data=b), mode="same")
    assert np.allclose(out.data, expected, rtol=1e-10, atol=1e-12)


def test_convolve_full_and_valid_shapes_and_extents():
    """full -> (Na+Nb-1, Ma+Mb-1); valid -> (Na-Nb+1, Ma-Mb+1); pixel size of
    field_a is preserved so physical extents scale proportionally."""
    from backend.nodes.convolve_two import ConvolveTwoImages

    rng = np.random.default_rng(5)
    a = rng.standard_normal((16, 12))
    b = rng.standard_normal((4, 3))
    field_a = make_field(data=a, xreal=2e-6, yreal=4e-6)
    node = ConvolveTwoImages()

    (full,) = node.process(field_a, make_field(data=b), mode="full")
    assert full.data.shape == (16 + 4 - 1, 12 + 3 - 1)
    assert np.isclose(full.xreal, field_a.xreal * full.data.shape[1] / 12)
    assert np.isclose(full.yreal, field_a.yreal * full.data.shape[0] / 16)
    assert np.allclose(full.data, convolve2d(a, b, mode="full"), rtol=1e-10, atol=1e-12)

    (valid,) = node.process(field_a, make_field(data=b), mode="valid")
    assert valid.data.shape == (16 - 4 + 1, 12 - 3 + 1)
    assert np.isclose(valid.xreal, field_a.xreal * valid.data.shape[1] / 12)
    assert np.allclose(valid.data, convolve2d(a, b, mode="valid"), rtol=1e-10, atol=1e-12)


def test_convolve_identity_kernel():
    """A unit impulse at the kernel centre reproduces the field in 'same' mode
    (kernel centred on the output pixel)."""
    from backend.nodes.convolve_two import ConvolveTwoImages

    rng = np.random.default_rng(6)
    a = rng.standard_normal((16, 16))
    kernel = np.zeros((3, 3))
    kernel[1, 1] = 1.0  # center of the 3x3 kernel aligns with the output pixel
    node = ConvolveTwoImages()
    (out,) = node.process(make_field(data=a), make_field(data=kernel), mode="same")
    assert np.allclose(out.data, a)
    # even kernel: centre sits 0.5 px towards lower indices (index kx//2), so an
    # impulse at (1,1) of a 4x4 kernel shifts the field up-left by one pixel,
    # with zero exterior at the far edges.
    kernel2 = np.zeros((4, 4))
    kernel2[1, 1] = 1.0
    (out2,) = node.process(make_field(data=a), make_field(data=kernel2), mode="same")
    # impulse at kernel index (1,1), centre at kx//2 = 2: out[j,i] = a[j+1, i+1]
    # with zero exterior -> a shifted up-left, zero at the last row/column.
    expected = np.zeros_like(a)
    expected[:-1, :-1] = a[1:, 1:]
    assert np.allclose(out2.data, expected, atol=1e-12)


def test_convolve_units():
    """Value units are the product of the two inputs' units."""
    from backend.nodes.convolve_two import ConvolveTwoImages

    field = make_field(data=np.ones((8, 8)))
    field.si_unit_z = "m"
    kernel = make_field(data=np.ones((3, 3)))
    kernel.si_unit_z = "m"
    node = ConvolveTwoImages()
    (out,) = node.process(field, kernel, mode="same")
    assert out.si_unit_z == "m^2"
    # dimensionless kernel keeps the field unit
    kernel2 = make_field(data=np.ones((3, 3)))
    kernel2.si_unit_z = ""
    (out2,) = node.process(field, kernel2, mode="same")
    assert out2.si_unit_z == "m"


def test_convolve_valid_kernel_too_large():
    from backend.nodes.convolve_two import ConvolveTwoImages

    field = make_field(data=np.ones((8, 8)))
    kernel = make_field(data=np.ones((10, 10)))
    node = ConvolveTwoImages()
    with pytest.raises(ValueError):
        node.process(field, kernel, mode="valid")
    # same/full modes tolerate any kernel size
    (out,) = node.process(field, kernel, mode="same")
    assert out.data.shape == (8, 8)
