"""
Node registry for argonode.

Nodes are plain Python classes decorated with @register_node.
NODE_CLASS_MAPPINGS is the single source of truth consumed by
the execution engine and the /nodes REST endpoint.
"""

from __future__ import annotations
from typing import Any

NODE_CLASS_MAPPINGS: dict[str, type] = {}
NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {}


def register_node(display_name: str | None = None):
    """
    Class decorator that registers a node class into NODE_CLASS_MAPPINGS.

    Usage:
        @register_node(display_name="Gaussian Filter")
        class GaussianFilter:
            ...
    """
    def decorator(cls: type) -> type:
        name = cls.__name__
        NODE_CLASS_MAPPINGS[name] = cls
        NODE_DISPLAY_NAME_MAPPINGS[name] = display_name or name
        return cls
    return decorator


def get_node_info(class_name: str) -> dict[str, Any]:
    """
    Return a JSON-serialisable dict describing a node — consumed by GET /nodes.
    Shape is compatible with what LiteGraph.js expects from the frontend.
    """
    cls = NODE_CLASS_MAPPINGS[class_name]
    input_types: dict = cls.INPUT_TYPES()

    return {
        "name": class_name,
        "display_name": NODE_DISPLAY_NAME_MAPPINGS.get(class_name, class_name),
        "category": getattr(cls, "CATEGORY", "uncategorized"),
        "input": input_types,
        "input_order": {k: list(v.keys()) for k, v in input_types.items()},
        "output": list(cls.RETURN_TYPES),
        "output_name": list(getattr(cls, "RETURN_NAMES", cls.RETURN_TYPES)),
        "output_node": bool(getattr(cls, "OUTPUT_NODE", False)),
        "description": getattr(cls, "DESCRIPTION", ""),
    }


def get_all_node_info() -> dict[str, dict[str, Any]]:
    """Return info dicts for every registered node."""
    return {name: get_node_info(name) for name in NODE_CLASS_MAPPINGS}
