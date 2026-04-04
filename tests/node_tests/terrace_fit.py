import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_terrace_fit_stepped_surface():
    from backend.nodes.terrace_fit import TerraceFit

    node = TerraceFit()
    # Create a surface with 3 clear terraces
    data = np.zeros((64, 64))
    data[:20, :] = 0.0
    data[20:40, :] = 1.0
    data[40:, :] = 2.0
    field = make_field(data=data)
    result, records = node.process(field, 3, 1.0, 0, "residual")
    assert result.data.shape == (64, 64)
    assert isinstance(records, list)
    assert len(records) >= 3  # at least terrace heights


def test_terrace_fit_auto_detect():
    from backend.nodes.terrace_fit import TerraceFit

    node = TerraceFit()
    data = np.zeros((64, 64))
    data[:32, :] = 0.0
    data[32:, :] = 5.0
    field = make_field(data=data)
    result, records = node.process(field, 0, 1.0, 0, "fitted")
    assert result.data.shape == (64, 64)


def test_terrace_fit_labels_output():
    from backend.nodes.terrace_fit import TerraceFit

    node = TerraceFit()
    data = np.zeros((32, 32))
    data[:16, :] = 1.0
    data[16:, :] = 3.0
    field = make_field(data=data)
    result, records = node.process(field, 2, 1.0, 0, "labels")
    assert result.data.shape == (32, 32)
    # Labels should have exactly 2 distinct values
    unique = np.unique(result.data)
    assert len(unique) == 2


def test_terrace_fit_step_heights_reported():
    from backend.nodes.terrace_fit import TerraceFit

    node = TerraceFit()
    data = np.zeros((64, 64))
    data[:32, :] = 0.0
    data[32:, :] = 2.5
    field = make_field(data=data)
    _, records = node.process(field, 2, 1.0, 0, "residual")
    # Should report step height
    step_records = [r for r in records if "Step" in r["quantity"]]
    assert len(step_records) >= 1
