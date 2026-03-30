"""
Node registry for argonode.

Nodes are plain Python classes decorated with @register_node.
NODE_CLASS_MAPPINGS is the single source of truth consumed by
the execution engine and the /nodes REST endpoint.
"""

from __future__ import annotations
from typing import Any

from backend.node_menu import get_menu_metadata

NODE_CLASS_MAPPINGS: dict[str, type] = {}
NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {}


def get_node_output_specs(cls: type) -> tuple[tuple[str, str, dict], ...]:
    raw_outputs = getattr(cls, "OUTPUTS", None)
    if raw_outputs is None:
        raise AttributeError(f"{cls.__name__} must define OUTPUTS.")

    specs: list[tuple[str, str, dict]] = []
    for index, output in enumerate(raw_outputs):
        if not isinstance(output, (list, tuple)) or len(output) not in (2, 3):
            raise TypeError(
                f"{cls.__name__}.OUTPUTS[{index}] must be a 2- or 3-item tuple of (type, name[, meta])."
            )
        type_name = output[0]
        name = output[1]
        meta: dict = output[2] if len(output) == 3 else {}
        specs.append((str(type_name), str(name), meta))
    return tuple(specs)


def get_node_output_types(cls: type) -> tuple[str, ...]:
    return tuple(type_name for type_name, _, _meta in get_node_output_specs(cls))


def get_node_output_names(cls: type) -> tuple[str, ...]:
    return tuple(name for _, name, _meta in get_node_output_specs(cls))


def get_node_output_accepted_types(cls: type) -> tuple[list[str], ...]:
    """Return per-slot accepted_types lists (empty list means only the declared type)."""
    return tuple(
        list(meta.get("accepted_types", []))
        for _, _, meta in get_node_output_specs(cls)
    )


def register_node(display_name: str | None = None):
    """
    Class decorator that registers a node class into NODE_CLASS_MAPPINGS.

    Usage:
        @register_node(display_name="Gaussian Filter")
        class GaussianFilter:
            ...
    """
    def decorator(cls: type) -> type:
        get_node_output_specs(cls)
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
    menu_metadata = get_menu_metadata(class_name)

    return {
        "name": class_name,
        "display_name": NODE_DISPLAY_NAME_MAPPINGS.get(class_name, class_name),
        "category": menu_metadata["category"],
        "category_order": menu_metadata["category_order"],
        "menu_order": menu_metadata["menu_order"],
        "menu_categories": list(menu_metadata.get("menu_categories", [])),
        "input": input_types,
        "input_order": {k: list(v.keys()) for k, v in input_types.items()},
        "output": list(get_node_output_types(cls)),
        "output_name": list(get_node_output_names(cls)),
        "output_accepted_types": list(get_node_output_accepted_types(cls)),
        "output_node": bool(getattr(cls, "OUTPUT_NODE", False)),
        "manual_trigger": bool(getattr(cls, "MANUAL_TRIGGER", False)),
        "description": getattr(cls, "DESCRIPTION", ""),
    }


def get_all_node_info() -> dict[str, dict[str, Any]]:
    """Return info dicts for every registered node."""
    return {name: get_node_info(name) for name in NODE_CLASS_MAPPINGS}
