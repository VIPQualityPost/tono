"""
Node registry for tono.

Nodes are plain Python classes decorated with @register_node.
NODE_CLASS_MAPPINGS is the single source of truth consumed by
the execution engine and the /nodes REST endpoint.
"""

from __future__ import annotations
from typing import Any

from backend.node_menu import get_menu_metadata

NODE_CLASS_MAPPINGS: dict[str, type] = {}
NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {}
# class name -> defining module, for collision detection and plugin reloads
NODE_CLASS_SOURCES: dict[str, str] = {}


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
        owner = cls.__module__
        existing = NODE_CLASS_MAPPINGS.get(name)
        if existing is not None and existing is not cls:
            current_owner = NODE_CLASS_SOURCES.get(name, "?")
            if current_owner != owner:
                raise ValueError(
                    f"Node class name '{name}' is already registered by module "
                    f"'{current_owner}' — refusing to silently overwrite it "
                    f"(new source '{owner}')."
                )
        NODE_CLASS_MAPPINGS[name] = cls
        NODE_DISPLAY_NAME_MAPPINGS[name] = display_name or name
        NODE_CLASS_SOURCES[name] = owner
        return cls
    return decorator


def module_registered_names(module_name: str) -> set[str]:
    """Node class names currently registered by *module_name*.

    Used by the plugin loader to diff registrations before/after a hot reload
    and drop nodes a plugin no longer defines. Package plugins register their
    sub-module classes under ``tono_plugins.<name>.<sub>``, so everything under
    the plugin namespace counts.
    """
    prefix = f"{module_name}."
    return {
        name for name, owner in NODE_CLASS_SOURCES.items()
        if owner == module_name or owner.startswith(prefix)
    }


def unregister_node(class_name: str) -> None:
    """Remove a node from the registry (plugin dropped the class on reload)."""
    owner = NODE_CLASS_SOURCES.pop(class_name, None)
    if owner is not None:
        NODE_CLASS_MAPPINGS.pop(class_name, None)
        NODE_DISPLAY_NAME_MAPPINGS.pop(class_name, None)


def get_node_info(class_name: str) -> dict[str, Any]:
    """
    Return a JSON-serialisable dict describing a node — consumed by GET /nodes.
    Shape is compatible with what LiteGraph.js expects from the frontend.
    """
    cls = NODE_CLASS_MAPPINGS[class_name]
    input_types: dict = cls.INPUT_TYPES()
    menu_metadata = get_menu_metadata(class_name, cls)

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
        "keywords": list(getattr(cls, "KEYWORDS", ())),
    }


def get_all_node_info() -> dict[str, dict[str, Any]]:
    """Return info dicts for every registered node."""
    return {name: get_node_info(name) for name in NODE_CLASS_MAPPINGS}
