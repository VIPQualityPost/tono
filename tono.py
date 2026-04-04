"""
tono — topographical signal processing library.

This module provides a convenient ``import tono`` entry point for using
tono's processing nodes as a standalone Python library, without running
the web server.

Quick start::

    import tono

    # Load SPM data
    fields = tono.load("scan.gwy")

    # Typed call syntax — help(tono.GaussianFilter) shows the signature
    result = tono.GaussianFilter(fields[0], sigma=3.0)

    # String-based dispatch for dynamic cases
    result = tono.apply("GaussianFilter", fields[0], sigma=3.0)

    # Create a field from a numpy array
    import numpy as np
    f = tono.field(np.random.randn(256, 256))

See ``backend.api`` for the full API documentation.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, Literal

from backend.api import (  # noqa: F401
    apply,
    channel_names,
    describe,
    field,
    get_node,
    load,
    nodes,
    supported_formats,
)
from backend.api import _ensure_registry as _ensure_registry
from backend.data_types import (  # noqa: F401
    DataField,
    DataTable,
    LineData,
    MeshModel,
    RecordTable,
)


# ── Runtime node wrappers ─────────────────────────────────────────────
#
# PEP 562 module __getattr__: expose every registered node as a
# top-level callable so users can write ``tono.GaussianFilter(field, sigma=2)``
# instead of ``tono.apply("GaussianFilter", field, sigma=2)``. Each wrapper
# carries a real inspect.Signature synthesised from the node's INPUT_TYPES,
# so help(tono.GaussianFilter), Jupyter's ``?``, and IPython tab-completion
# all show the correct parameters, defaults, and enum choices.

_NODE_WRAPPER_CACHE: dict[str, Callable[..., Any]] = {}


# Map tono type-system names to Python runtime types used in annotations.
# Unknown names fall back to ``typing.Any``.
_TONO_TYPE_MAP: dict[str, Any] = {
    "DATA_FIELD": DataField,
    "IMAGE": DataField,
    "FLOAT": float,
    "INT": int,
    "STRING": str,
    "BOOL": bool,
    "LINE": LineData,
    "RECORD_TABLE": RecordTable,
    "TABLE": RecordTable,
    "DATA_TABLE": DataTable,
    "MESH": MeshModel,
    "COORD": tuple,
}


def _tono_type_to_python(spec: Any) -> Any:
    """Resolve a tono input/output type spec to a Python annotation.

    ``spec`` is the first element of an INPUT_TYPES tuple — either a string
    type name (``"FLOAT"``) or a list of choices (``["sobel", "prewitt"]``).
    """
    if isinstance(spec, (list, tuple)) and all(isinstance(x, str) for x in spec):
        # Enum input — use typing.Literal so help() shows the exact choices.
        if len(spec) == 0:
            return str
        return Literal[tuple(spec)]  # type: ignore[valid-type]
    if isinstance(spec, str):
        return _TONO_TYPE_MAP.get(spec, Any)
    return Any


def _build_node_wrapper(name: str, cls: type) -> Callable[..., Any]:
    """Build a callable wrapper with a synthesised inspect.Signature for ``cls``."""
    input_types = cls.INPUT_TYPES()
    required = input_types.get("required", {})
    optional = input_types.get("optional", {})

    params: list[inspect.Parameter] = []
    param_doc_lines: list[str] = []
    EMPTY = inspect.Parameter.empty

    def _param(arg_name: str, raw_spec: Any, force_optional: bool) -> None:
        # raw_spec is a tuple like ("FLOAT", {...}) or (["sobel","prewitt"],)
        type_token = raw_spec[0] if isinstance(raw_spec, (list, tuple)) and raw_spec else raw_spec
        meta: dict = {}
        if isinstance(raw_spec, (list, tuple)) and len(raw_spec) >= 2 and isinstance(raw_spec[1], dict):
            meta = raw_spec[1]

        annotation = _tono_type_to_python(type_token)
        if force_optional:
            default: Any = None
        elif "default" in meta:
            default = meta["default"]
        else:
            default = EMPTY

        params.append(
            inspect.Parameter(
                arg_name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default,
                annotation=annotation,
            )
        )

        # Docstring line
        if isinstance(type_token, (list, tuple)):
            type_desc = "{" + ", ".join(repr(c) for c in type_token) + "}"
        elif isinstance(type_token, str):
            type_desc = type_token
        else:
            type_desc = "Any"
        default_desc = "" if default is EMPTY else f" (default: {default!r})"
        param_doc_lines.append(f"    {arg_name} : {type_desc}{default_desc}")

    for arg_name, raw_spec in required.items():
        _param(arg_name, raw_spec, force_optional=False)

    # Python signatures require that any parameter with a default is followed
    # only by parameters that also have defaults. Some nodes declare required
    # inputs in an order that violates this (e.g. ThresholdMask has ``threshold``
    # with a default followed by ``direction`` without). Walk the required
    # params in reverse and clear defaults that would break ordering — the
    # default still fires at runtime via apply()'s metadata default-filling,
    # it just isn't displayed in the signature for that slot.
    _seen_no_default = False
    for i in range(len(params) - 1, -1, -1):
        if params[i].default is EMPTY:
            _seen_no_default = True
        elif _seen_no_default:
            params[i] = params[i].replace(default=EMPTY)

    for arg_name, raw_spec in optional.items():
        _param(arg_name, raw_spec, force_optional=True)

    # Return annotation: single-output nodes return the unwrapped Python type;
    # multi-output nodes return a tuple.
    outputs = getattr(cls, "OUTPUTS", ())
    if len(outputs) == 1:
        return_annotation: Any = _tono_type_to_python(outputs[0][0])
    else:
        return_annotation = tuple

    signature = inspect.Signature(params, return_annotation=return_annotation)

    description = (getattr(cls, "DESCRIPTION", "") or "").strip()
    output_lines = [
        f"    {out_name} : {out_type}"
        for out_type, out_name, *_ in outputs
    ]

    doc_parts: list[str] = []
    if description:
        doc_parts.append(description)
    doc_parts.append("")
    doc_parts.append("Parameters")
    doc_parts.append("----------")
    doc_parts.extend(param_doc_lines if param_doc_lines else ["    (none)"])
    if output_lines:
        doc_parts.append("")
        doc_parts.append("Returns")
        doc_parts.append("-------")
        doc_parts.extend(output_lines)
    docstring = "\n".join(doc_parts)

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return apply(name, *args, **kwargs)

    wrapper.__name__ = name
    wrapper.__qualname__ = f"tono.{name}"
    wrapper.__module__ = "tono"
    wrapper.__doc__ = docstring
    wrapper.__signature__ = signature  # type: ignore[attr-defined]
    wrapper.__wrapped_node__ = name  # type: ignore[attr-defined]
    return wrapper


def __getattr__(name: str) -> Any:
    # Skip dunder lookups so imports, pickling, and debuggers don't trigger
    # registry loading or spurious AttributeError chains.
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(f"module 'tono' has no attribute {name!r}")

    from backend.node_registry import NODE_CLASS_MAPPINGS

    _ensure_registry()
    if name not in NODE_CLASS_MAPPINGS:
        raise AttributeError(f"module 'tono' has no attribute {name!r}")

    cached = _NODE_WRAPPER_CACHE.get(name)
    if cached is None:
        cached = _build_node_wrapper(name, NODE_CLASS_MAPPINGS[name])
        _NODE_WRAPPER_CACHE[name] = cached
    return cached


def __dir__() -> list[str]:
    from backend.node_registry import NODE_CLASS_MAPPINGS

    _ensure_registry()
    return sorted({*globals().keys(), *NODE_CLASS_MAPPINGS.keys()})
