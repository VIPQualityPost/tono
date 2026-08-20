import numpy as np
import pytest

from backend.node_registry import get_node_info
from tests.node_tests._shared import make_field


def test_step_block_correction_full_width_step():
    from backend.nodes.step_block_correction import StepBlockCorrection

    node = StepBlockCorrection()
    assert get_node_info("StepBlockCorrection")["category"] == "Level & Correct"
    assert len(node.OUTPUTS) == 2

    rows, cols = 64, 128
    xx, yy = np.meshgrid(np.linspace(0.0, 1.0, cols), np.linspace(0.0, 1.0, rows))
    # Smooth base whose own row-to-row variation is far below the threshold
    # (the step dominates the RMS vertical difference).
    base = 0.2 * np.sin(2.0 * np.pi * xx) + 0.005 * np.sin(2.0 * np.pi * yy)
    step = 0.5
    row0 = 20
    data = base.copy()
    data[row0:] += step
    field = make_field(data=data, xreal=2e-6, yreal=1e-6)

    corrected, stats = node.process(field, threshold=2.0, scan_direction="left_to_right")

    assert corrected.data.shape == field.data.shape
    assert corrected.si_unit_z == field.si_unit_z
    assert corrected.si_unit_xy == field.si_unit_xy
    assert corrected.xreal == field.xreal
    assert not np.shares_memory(corrected.data, field.data)

    # The field is restored to the smooth base; the step jump is gone.
    assert np.allclose(corrected.data, base, atol=0.05)
    jump = np.abs(np.diff(corrected.data, axis=0)).mean()
    assert jump < 0.03

    quantities = [row["quantity"] for row in stats]
    assert "Detected blocks" in quantities
    assert "Block 1 step" in quantities
    step_row = next(row for row in stats if row["quantity"] == "Block 1 step")
    assert step_row["unit"] == field.si_unit_z
    assert np.isclose(step_row["value"], step, atol=0.02)
    block_row = next(row for row in stats if row["quantity"] == "Block 1 row")
    assert block_row["value"] == row0


def test_step_block_correction_score_above_minlength():
    """A partial step covering >= 3/4 of the width is still detected."""
    from backend.nodes.step_block_correction import StepBlockCorrection

    node = StepBlockCorrection()

    rows, cols = 64, 128
    data = np.zeros((rows, cols))
    step = 0.4
    row0, c0 = 24, 20  # 108/128 >= 3/4 coverage
    data[row0:, c0:] += step
    field = make_field(data=data)

    corrected, stats = node.process(field, threshold=2.0, scan_direction="left_to_right")
    quantities = [row["quantity"] for row in stats]
    assert "Block 1 step" in quantities
    # Right part below the step restored.
    assert np.allclose(corrected.data[row0:, c0:], 0.0, atol=0.02)
    assert np.allclose(corrected.data[:row0, c0:], 0.0, atol=0.02)


def test_step_block_correction_threshold_skips():
    from backend.nodes.step_block_correction import StepBlockCorrection

    node = StepBlockCorrection()

    rows, cols = 64, 128
    rng = np.random.default_rng(5)
    base = rng.standard_normal((rows, cols)) * 0.1
    data = base.copy()
    data[20:] += 0.5
    field = make_field(data=data)

    # The RMS vertical difference of the noisy base is ~0.14; a threshold of
    # 10 times it (1.4) is far above the 0.5 step, so nothing is detected.
    corrected, stats = node.process(field, threshold=10.0, scan_direction="left_to_right")
    assert np.allclose(corrected.data, field.data)
    assert [row["quantity"] for row in stats] == ["Detected blocks"]
    assert stats[0]["value"] == 0


def test_step_block_correction_right_to_left():
    from backend.nodes.step_block_correction import StepBlockCorrection

    node = StepBlockCorrection()

    rows, cols = 64, 128
    data = np.zeros((rows, cols))
    data[30:] += 0.3
    field = make_field(data=data)

    corrected, stats = node.process(field, threshold=2.0, scan_direction="right_to_left")
    quantities = [row["quantity"] for row in stats]
    assert "Block 1 step" in quantities
    assert np.allclose(corrected.data[30:], 0.0, atol=0.02)
    jump = np.abs(np.diff(corrected.data, axis=0)).mean()
    assert jump < 1e-3


def test_step_block_correction_errors():
    from backend.nodes.step_block_correction import StepBlockCorrection

    node = StepBlockCorrection()
    field = make_field()

    with pytest.raises(ValueError, match="scan direction"):
        node.process(field, threshold=2.0, scan_direction="bogus")

    with pytest.raises(ValueError, match="2D"):
        bad = field.replace(data=np.zeros(5))
        node.process(bad, threshold=2.0, scan_direction="left_to_right")


def test_step_block_correction_output_arity():
    from backend.nodes.step_block_correction import StepBlockCorrection

    node = StepBlockCorrection()
    field = make_field()
    result = node.process(field, threshold=2.0, scan_direction="left_to_right")
    assert len(result) == 2
    from backend.data_types import RecordTable

    assert isinstance(result[1], RecordTable)
