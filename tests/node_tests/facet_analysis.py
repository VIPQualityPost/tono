import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_facet_analysis_basic():
    from backend.nodes.facet_analysis import FacetAnalysis

    node = FacetAnalysis()
    field = make_field(shape=(64, 64))
    result, = node.process(field, 180, 3)
    assert result.data.ndim == 2
    assert result.si_unit_xy == "deg"


def test_facet_analysis_flat_field():
    from backend.nodes.facet_analysis import FacetAnalysis

    node = FacetAnalysis()
    field = make_field(data=np.zeros((32, 32)))
    result, = node.process(field, 180, 3)
    assert result.data.ndim == 2


def test_facet_analysis_density_normalised():
    from backend.nodes.facet_analysis import FacetAnalysis

    node = FacetAnalysis()
    field = make_field(shape=(64, 64))
    result, = node.process(field, 180, 3)
    # Should be a normalised probability density
    assert np.isclose(result.data.sum(), 1.0, atol=1e-10)


def test_facet_analysis_bin_count():
    from backend.nodes.facet_analysis import FacetAnalysis

    node = FacetAnalysis()
    field = make_field(shape=(64, 64))
    result, = node.process(field, 360, 3)
    # phi bins = n_bins, theta bins = n_bins // 4
    assert result.data.shape == (90, 360)
