"""
Standalone library API for tono signal processing nodes.

Usage::

    import tono

    # Load an SPM file
    fields = tono.load("scan.gwy")
    field = fields[0]

    # Apply a processing node
    result = tono.apply("GaussianFilter", field, sigma=3.0)

    # Chain operations
    result = tono.apply("PlaneLevelField", field, mode="subtract_mean")
    result = tono.apply("GaussianFilter", result, sigma=2.0)

    # Get available nodes
    print(tono.nodes())

    # Direct node access
    node = tono.get_node("GaussianFilter")
    (filtered,) = node.process(field=field, sigma=3.0)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.data_types import DataField, LineData, RecordTable, DataTable, MeshModel


def _ensure_registry() -> None:
    """Import all node modules so @register_node decorators fire."""
    from backend.node_registry import NODE_CLASS_MAPPINGS
    if NODE_CLASS_MAPPINGS:
        return
    import backend.nodes  # noqa: F401 — triggers auto-discovery


def load(path: str | Path) -> list[DataField]:
    """Load an SPM data file and return a list of DataField channels.

    Supported formats: .gwy, .sxm, .ibw, .hdf5, .png, .tif, .jpg, and more.

    Parameters
    ----------
    path : str or Path
        Path to the data file.

    Returns
    -------
    list[DataField]
        One DataField per channel in the file.

    Raises
    ------
    ValueError
        If the file extension is not supported.
    """
    from backend.importers import get_importer

    p = Path(path)
    ext = p.suffix.lower()
    importer = get_importer(ext)
    if importer is None:
        from backend.importers import all_extensions
        supported = ", ".join(sorted(all_extensions()))
        raise ValueError(
            f"Unsupported file extension {ext!r}. Supported: {supported}"
        )
    return importer.load(str(p))


def channel_names(path: str | Path) -> list[str]:
    """Return the channel names in a data file without loading the full data."""
    from backend.importers import get_importer

    p = Path(path)
    importer = get_importer(p.suffix.lower())
    if importer is None:
        raise ValueError(f"Unsupported file extension: {p.suffix!r}")
    return importer.channel_names(str(p))


def supported_formats() -> frozenset[str]:
    """Return all supported file extensions (e.g. {'.gwy', '.sxm', ...})."""
    from backend.importers import all_extensions
    return all_extensions()


def nodes() -> list[str]:
    """Return a sorted list of all registered node class names."""
    from backend.node_registry import NODE_CLASS_MAPPINGS
    _ensure_registry()
    return sorted(NODE_CLASS_MAPPINGS.keys())


def get_node(class_name: str) -> Any:
    """Return a fresh instance of the named node class.

    Parameters
    ----------
    class_name : str
        The node class name, e.g. ``"GaussianFilter"``.

    Returns
    -------
    object
        A node instance. Call its ``process(**kwargs)`` method to run it.

    Raises
    ------
    KeyError
        If no node with that name is registered.
    """
    from backend.node_registry import NODE_CLASS_MAPPINGS
    _ensure_registry()
    if class_name not in NODE_CLASS_MAPPINGS:
        raise KeyError(
            f"Unknown node {class_name!r}. "
            f"Use tono.nodes() to list available nodes."
        )
    return NODE_CLASS_MAPPINGS[class_name]()


def apply(class_name: str, *args: Any, **kwargs: Any) -> Any:
    """Run a node's process function and return the result.

    Positional arguments are mapped to the node's required inputs in order.
    Keyword arguments are passed directly.

    If the node returns a single output, it is unwrapped from the tuple.
    If the node returns multiple outputs, the full tuple is returned.

    Parameters
    ----------
    class_name : str
        The node class name, e.g. ``"GaussianFilter"``.
    *args
        Positional arguments mapped to required inputs in declaration order.
    **kwargs
        Keyword arguments passed directly to the node's process function.

    Returns
    -------
    DataField or tuple
        Single output unwrapped, or tuple of outputs if multiple.

    Examples
    --------
    >>> result = tono.apply("GaussianFilter", field, sigma=3.0)
    >>> leveled, mask = tono.apply("PlaneLevelField", field, mode="subtract_mean")
    """
    from backend.node_registry import NODE_CLASS_MAPPINGS
    from backend.execution_context import execution_callbacks, active_node

    _ensure_registry()
    if class_name not in NODE_CLASS_MAPPINGS:
        raise KeyError(
            f"Unknown node {class_name!r}. "
            f"Use tono.nodes() to list available nodes."
        )

    cls = NODE_CLASS_MAPPINGS[class_name]
    instance = cls()

    # Map positional args to required input names in declaration order
    if args:
        input_types = cls.INPUT_TYPES()
        required_names = list(input_types.get("required", {}).keys())
        for i, arg in enumerate(args):
            if i >= len(required_names):
                raise TypeError(
                    f"{class_name} has {len(required_names)} required inputs, "
                    f"but {len(args)} positional arguments were given"
                )
            name = required_names[i]
            if name in kwargs:
                raise TypeError(
                    f"{class_name}: input {name!r} specified both as positional "
                    f"argument and keyword argument"
                )
            kwargs[name] = arg

    func = getattr(instance, cls.FUNCTION)

    # Run inside an execution context so emit_* calls are no-ops
    with execution_callbacks(), active_node("api"):
        result = func(**kwargs)

    if not isinstance(result, tuple):
        result = (result,)

    return result[0] if len(result) == 1 else result


def field(data: Any, xreal: float = 1e-6, yreal: float = 1e-6,
          si_unit_xy: str = "m", si_unit_z: str = "m", **kwargs: Any) -> DataField:
    """Create a DataField from a 2D array.

    A convenience wrapper around ``DataField(...)`` with sensible defaults.

    Parameters
    ----------
    data : array_like
        2D numpy array or anything convertible to one.
    xreal : float
        Physical width in metres (default 1 um).
    yreal : float
        Physical height in metres (default 1 um).
    si_unit_xy : str
        Lateral unit string (default "m").
    si_unit_z : str
        Height/value unit string (default "m").
    **kwargs
        Additional DataField keyword arguments.

    Returns
    -------
    DataField
    """
    import numpy as np
    return DataField(
        data=np.asarray(data, dtype=np.float64),
        xreal=xreal,
        yreal=yreal,
        si_unit_xy=si_unit_xy,
        si_unit_z=si_unit_z,
        **kwargs,
    )
