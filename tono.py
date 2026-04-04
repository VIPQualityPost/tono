"""
tono — topographical signal processing library.

This module provides a convenient ``import tono`` entry point for using
tono's processing nodes as a standalone Python library, without running
the web server.

Quick start::

    import tono

    # Load SPM data
    fields = tono.load("scan.gwy")

    # Process
    result = tono.apply("GaussianFilter", fields[0], sigma=3.0)

    # Create a field from a numpy array
    import numpy as np
    f = tono.field(np.random.randn(256, 256))

See ``backend.api`` for the full API documentation.
"""

from backend.api import (  # noqa: F401
    apply,
    channel_names,
    field,
    get_node,
    load,
    nodes,
    supported_formats,
)
from backend.data_types import (  # noqa: F401
    DataField,
    DataTable,
    LineData,
    MeshModel,
    RecordTable,
)
