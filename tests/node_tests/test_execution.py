import backend.nodes  # noqa: F401 — registers all nodes
from backend.execution import ExecutionEngine
from backend.node_registry import register_node


def test_execution_engine_numeric_socket_coercion():
    @register_node(display_name="Test Echo Int")
    class TestEchoInt:
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("INT",)}}
        OUTPUTS = (('INT', 'value'),)
        FUNCTION = "process"
        CATEGORY = "tests"
        def process(self, value):
            return (value,)

    @register_node(display_name="Test Echo Float")
    class TestEchoFloat:
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("FLOAT",)}}
        OUTPUTS = (('FLOAT', 'value'),)
        FUNCTION = "process"
        CATEGORY = "tests"
        def process(self, value):
            return (value,)

    engine = ExecutionEngine()
    prompt = {
        "1": {"class_type": "Number", "inputs": {"value": 3.6}},
        "2": {"class_type": "TestEchoInt", "inputs": {"value": ["1", 0]}},
        "3": {"class_type": "TestEchoFloat", "inputs": {"value": ["1", 0]}},
    }

    outputs = engine.execute(prompt)
    assert outputs["2"] == (4,)
    assert outputs["3"] == (3.6,)


def test_execution_engine_caches_unchanged_nodes():
    @register_node(display_name="Test Cache Source")
    class TestCacheSource:
        calls = 0
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("FLOAT",)}}
        OUTPUTS = (('FLOAT', 'value'),)
        FUNCTION = "process"
        CATEGORY = "tests"
        def process(self, value):
            TestCacheSource.calls += 1
            return (float(value),)

    @register_node(display_name="Test Cache Downstream")
    class TestCacheDownstream:
        calls = 0
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("FLOAT",)}}
        OUTPUTS = (('FLOAT', 'value'),)
        FUNCTION = "process"
        CATEGORY = "tests"
        def process(self, value):
            TestCacheDownstream.calls += 1
            return (float(value) * 2.0,)

    TestCacheSource.calls = 0
    TestCacheDownstream.calls = 0

    engine = ExecutionEngine()
    prompt = {
        "1": {"class_type": "TestCacheSource", "inputs": {"value": 2.5}},
        "2": {"class_type": "TestCacheDownstream", "inputs": {"value": ["1", 0]}},
    }

    first_timings = []
    first_outputs = engine.execute(prompt, on_node_done=lambda node_id, elapsed_ms: first_timings.append((node_id, elapsed_ms)))
    second_timings = []
    second_outputs = engine.execute(prompt, on_node_done=lambda node_id, elapsed_ms: second_timings.append((node_id, elapsed_ms)))

    assert first_outputs["2"] == (5.0,)
    assert second_outputs["2"] == (5.0,)
    assert TestCacheSource.calls == 1
    assert TestCacheDownstream.calls == 1
    assert {node_id for node_id, _ in second_timings} == {"1", "2"}
    assert all(elapsed_ms == 0.0 for _, elapsed_ms in second_timings)


def test_execution_engine_only_propagates_real_output_changes():
    @register_node(display_name="Test Quantized Source")
    class TestQuantizedSource:
        calls = 0
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("FLOAT",)}}
        OUTPUTS = (('INT', 'value'),)
        FUNCTION = "process"
        CATEGORY = "tests"
        def process(self, value):
            TestQuantizedSource.calls += 1
            return (int(round(float(value))),)

    @register_node(display_name="Test Quantized Downstream")
    class TestQuantizedDownstream:
        calls = 0
        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"value": ("INT",)}}
        OUTPUTS = (('FLOAT', 'value'),)
        FUNCTION = "process"
        CATEGORY = "tests"
        def process(self, value):
            TestQuantizedDownstream.calls += 1
            return (float(value) + 0.5,)

    TestQuantizedSource.calls = 0
    TestQuantizedDownstream.calls = 0

    engine = ExecutionEngine()
    prompt = {
        "1": {"class_type": "TestQuantizedSource", "inputs": {"value": 1.2}},
        "2": {"class_type": "TestQuantizedDownstream", "inputs": {"value": ["1", 0]}},
    }

    outputs_first = engine.execute(prompt)
    assert outputs_first["2"] == (1.5,)

    prompt["1"]["inputs"]["value"] = 1.3
    outputs_second = engine.execute(prompt)
    assert outputs_second["2"] == (1.5,)

    prompt["1"]["inputs"]["value"] = 2.2
    outputs_third = engine.execute(prompt)
    assert outputs_third["2"] == (2.5,)

    assert TestQuantizedSource.calls == 3
    assert TestQuantizedDownstream.calls == 2
