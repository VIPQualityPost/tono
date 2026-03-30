"""Tests for ExecutionEngine._auto_preview and _render_line_preview."""
import backend.nodes  # noqa: F401
import numpy as np
from backend.execution import ExecutionEngine
from backend.node_registry import register_node
from backend.data_types import DataField, LineData


def test_auto_preview_data_field():
    """A node that outputs DATA_FIELD should trigger on_preview."""
    engine = ExecutionEngine()
    previews = []
    prompt = {
        "1": {"class_type": "Number", "inputs": {"value": 1.0}},
    }
    # Number outputs FLOAT, not DATA_FIELD — use GaussianFilter which outputs DATA_FIELD
    from tests.node_tests._shared import make_field

    @register_node(display_name="Test Preview Field Source")
    class TestPreviewFieldSource:
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {}}
        OUTPUTS = (('DATA_FIELD', 'out'),)
        FUNCTION = "process"
        CATEGORY = "tests"
        def process(self):
            return (make_field(),)

    engine = ExecutionEngine()
    previews = []
    prompt = {"1": {"class_type": "TestPreviewFieldSource", "inputs": {}}}
    engine.execute(prompt, on_preview=lambda nid, p: previews.append((nid, p)))
    assert len(previews) == 1
    nid, payload = previews[0]
    assert nid == "1"
    assert isinstance(payload, str) and payload.startswith("data:image/png;base64,")


def test_auto_preview_line():
    """A node that outputs LINE should trigger on_preview with a line_plot dict."""
    @register_node(display_name="Test Preview Line Source")
    class TestPreviewLineSource:
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {}}
        OUTPUTS = (('LINE', 'out'),)
        FUNCTION = "process"
        CATEGORY = "tests"
        def process(self):
            return (LineData(
                data=np.sin(np.linspace(0, 2 * np.pi, 64)),
                x_axis=np.linspace(0, 1e-6, 64),
                x_unit="m",
            ),)

    engine = ExecutionEngine()
    previews = []
    prompt = {"1": {"class_type": "TestPreviewLineSource", "inputs": {}}}
    engine.execute(prompt, on_preview=lambda nid, p: previews.append((nid, p)))
    assert len(previews) == 1
    _, payload = previews[0]
    assert isinstance(payload, dict)
    assert payload["kind"] == "line_plot"
    assert "line" in payload and "x_axis" in payload
    assert payload["x_unit"] == "m"


def test_auto_preview_table():
    """A node that outputs RECORD_TABLE should trigger on_table."""
    from backend.data_types import RecordTable

    @register_node(display_name="Test Preview Table Source")
    class TestPreviewTableSource:
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {}}
        OUTPUTS = (('RECORD_TABLE', 'out'),)
        FUNCTION = "process"
        CATEGORY = "tests"
        def process(self):
            return (RecordTable([{"quantity": "x", "value": 1.0, "unit": "m"}]),)

    engine = ExecutionEngine()
    tables = []
    prompt = {"1": {"class_type": "TestPreviewTableSource", "inputs": {}}}
    engine.execute(prompt, on_table=lambda nid, t: tables.append((nid, t)))
    assert len(tables) == 1
    nid, rows = tables[0]
    assert nid == "1"
    assert rows[0]["quantity"] == "x"


def test_auto_preview_polymorphic_field_output():
    """A polymorphic output (declared LINE, actual DataField) should preview as a field."""
    from tests.node_tests._shared import make_field

    @register_node(display_name="Test Polymorphic Field Out")
    class TestPolymorphicFieldOut:
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {}}
        OUTPUTS = (('LINE', 'out', {"accepted_types": ["DATA_FIELD"]}),)
        FUNCTION = "process"
        CATEGORY = "tests"
        def process(self):
            return (make_field(),)

    engine = ExecutionEngine()
    previews = []
    prompt = {"1": {"class_type": "TestPolymorphicFieldOut", "inputs": {}}}
    engine.execute(prompt, on_preview=lambda nid, p: previews.append((nid, p)))
    assert len(previews) == 1
    _, payload = previews[0]
    # Should render as field preview (data URI), not line_plot dict
    assert isinstance(payload, str) and payload.startswith("data:image/png;base64,")


def test_on_node_start_called():
    """on_node_start callback fires before each node executes."""
    @register_node(display_name="Test Start Callback")
    class TestStartCallback:
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {}}
        OUTPUTS = (('FLOAT', 'v'),)
        FUNCTION = "process"
        CATEGORY = "tests"
        def process(self):
            return (1.0,)

    started = []
    engine = ExecutionEngine()
    prompt = {"1": {"class_type": "TestStartCallback", "inputs": {}}}
    engine.execute(prompt, on_node_start=lambda nid: started.append(nid))
    assert started == ["1"]
