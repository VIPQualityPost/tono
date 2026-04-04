import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_output_shape():
    from backend.nodes.psdf_log_polar import LogPolarPSDF

    node = LogPolarPSDF()
    field = make_field()
    (psdf,) = node.process(field, n_phi=90, n_r=50)
    assert psdf.data.shape == (50, 90)


def test_nonnegative():
    from backend.nodes.psdf_log_polar import LogPolarPSDF

    node = LogPolarPSDF()
    field = make_field()
    (psdf,) = node.process(field, n_phi=180, n_r=100)
    assert np.all(psdf.data >= 0), "log1p of power should be non-negative"


def test_domain():
    from backend.nodes.psdf_log_polar import LogPolarPSDF

    node = LogPolarPSDF()
    field = make_field()
    (psdf,) = node.process(field, n_phi=180, n_r=100)
    assert psdf.domain == "frequency"
