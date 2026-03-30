"""
Calls get_node_info() for every registered node to ensure INPUT_TYPES()
is exercised and the registry metadata is well-formed.
"""
import backend.nodes  # noqa: F401 — registers all nodes
from backend.node_registry import get_node_info, NODE_CLASS_MAPPINGS


_REQUIRED_KEYS = {"name", "display_name", "category", "input", "output", "output_name", "description"}


def test_all_nodes_have_valid_info():
    for class_name in NODE_CLASS_MAPPINGS:
        info = get_node_info(class_name)
        missing = _REQUIRED_KEYS - info.keys()
        assert not missing, f"{class_name} info missing keys: {missing}"
        assert isinstance(info["input"], dict), f"{class_name} input must be a dict"
        assert isinstance(info["output"], list), f"{class_name} output must be a list"
        assert isinstance(info["output_name"], list), f"{class_name} output_name must be a list"
        assert len(info["output"]) == len(info["output_name"]), (
            f"{class_name} output/output_name length mismatch"
        )


def test_all_nodes_input_types_callable():
    """INPUT_TYPES() must return a dict with at least a 'required' or 'optional' key."""
    for class_name, cls in NODE_CLASS_MAPPINGS.items():
        result = cls.INPUT_TYPES()
        assert isinstance(result, dict), f"{class_name}.INPUT_TYPES() must return a dict"
        assert "required" in result or "optional" in result, (
            f"{class_name}.INPUT_TYPES() must have 'required' or 'optional'"
        )
