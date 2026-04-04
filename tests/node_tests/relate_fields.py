import numpy as np
import pytest
from tests.node_tests._shared import make_field


def test_linear_fit():
    from backend.nodes.relate_fields import RelateFields

    node = RelateFields()
    rng = np.random.default_rng(42)
    a_data = rng.uniform(0.5, 5.0, (32, 32))
    b_data = 2.0 * a_data + 1.0
    field_a = make_field(data=a_data)
    field_b = make_field(data=b_data)

    predicted, records = node.process(field_a, field_b, function="linear")

    params = {r["quantity"]: r["value"] for r in records}
    assert float(params["slope"]) == pytest.approx(2.0, abs=1e-6)
    assert float(params["intercept"]) == pytest.approx(1.0, abs=1e-6)
    assert float(params["R\u00b2"]) == pytest.approx(1.0, abs=1e-6)


def test_r_squared_reported():
    from backend.nodes.relate_fields import RelateFields

    node = RelateFields()
    rng = np.random.default_rng(0)
    field_a = make_field(data=rng.standard_normal((32, 32)))
    field_b = make_field(data=rng.standard_normal((32, 32)))

    _, records = node.process(field_a, field_b, function="linear")
    quantities = [r["quantity"] for r in records]
    assert "R\u00b2" in quantities, f"Expected 'R\u00b2' in {quantities}"


def test_power_fit():
    from backend.nodes.relate_fields import RelateFields

    node = RelateFields()
    rng = np.random.default_rng(99)
    a_data = rng.uniform(1.0, 10.0, (32, 32))
    # b = 3.0 * a^2.0
    b_data = 3.0 * np.power(a_data, 2.0)
    field_a = make_field(data=a_data)
    field_b = make_field(data=b_data)

    predicted, records = node.process(field_a, field_b, function="power")

    params = {r["quantity"]: r["value"] for r in records}
    assert "exponent" in params, f"Expected 'exponent' in {params}"
    assert "coefficient" in params, f"Expected 'coefficient' in {params}"
    assert float(params["exponent"]) == pytest.approx(2.0, abs=0.05)
    assert float(params["coefficient"]) == pytest.approx(3.0, abs=0.1)
