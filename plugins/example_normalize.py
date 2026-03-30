"""
Example tono plugin: Normalize Z Range

Drop any .py file into this plugins/ folder and restart tono (or upload it
via POST /upload-plugin) — the node will appear in the Add Node menu immediately.

─── What you need to import ─────────────────────────────────────────────────

  from backend.node_registry import register_node   ← the decorator
  from backend.data_types import DataField           ← the main SPM data type

Other available types (import from backend.data_types as needed):
  LineData    - 1-D profile data (data, x_axis arrays + units)
  MeshModel   - 3-D triangle mesh (vertices, faces, colors arrays)
  RecordTable - measurement table (list of dicts with schema)
  IMAGE       - uint8 numpy array (masks, greyscale, RGB images)

─── Input types you can declare in INPUT_TYPES ──────────────────────────────

  ("DATA_FIELD",)              - SPM height/signal field
  ("IMAGE",)                   - mask or image (uint8 ndarray)
  ("LINE",)                    - 1-D line/profile data
  ("FLOAT", {...options...})   - float number widget
  ("INT",   {...options...})   - integer number widget
  (["choice_a", "choice_b"],)  - dropdown menu
  ("STRING", {...})            - text input

─── Output types you can declare in OUTPUTS ─────────────────────────────────

  ("DATA_FIELD", "name")    - SPM field
  ("IMAGE",      "name")    - mask / image
  ("LINE",       "name")    - 1-D data
  ("FLOAT",      "name")    - scalar number
  ("RECORD_TABLE","name")   - measurement table

─── Inputs are passed as keyword arguments to your process() method ─────────
─── Outputs must be returned as a tuple, one item per OUTPUTS entry ─────────
"""

import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable


@register_node(display_name="Normalize Z Range")
class NormalizeZRange:
    """Rescale height values so the full range maps to [low, high]."""

    # Menu category shown in the Add Node popup.
    # Any string works; nodes sharing a category are grouped together.
    CATEGORY = "Plugins"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # DATA_FIELD is the standard SPM field type.
                "field": ("DATA_FIELD",),

                # FLOAT widget with default, min, and max.
                "low": ("FLOAT", {"default": 0.0}),
                "high": ("FLOAT", {"default": 1.0}),
            },
            # Optional inputs don't need to be connected.
            "optional": {
                # A mask (uint8, 0 or 255) can restrict which pixels are
                # used to compute the min/max for normalisation.
                "mask": ("IMAGE",),
            },
        }

    # Each entry is (output_type, output_name).
    # The tuple length must match the tuple returned by process().
    OUTPUTS = (
        ("DATA_FIELD", "normalized"),
        # RECORD_TABLE outputs appear as a "Print Table" connector and can be
        # wired to the PrintTable display node or the Save node (CSV/JSON).
        # The table is a RecordTable — a plain list of dicts, each with the
        # keys "quantity", "value", and "unit".
        ("RECORD_TABLE", "stats"),
    )

    # Name of the method to call when the node executes.
    FUNCTION = "process"

    DESCRIPTION = (
        "Linearly rescale the Z values so the full data range maps to "
        "[low, high].  If a mask is connected, only masked pixels are used "
        "to compute the source min/max (unmasked pixels are still rescaled).  "
        "Also outputs a measurement table with the source range statistics."
    )

    def process(
        self,
        field: DataField,
        low: float,
        high: float,
        mask=None,          # optional: uint8 ndarray or None
    ) -> tuple:
        data = field.data.astype(np.float64)

        # Determine the source range from masked pixels if a mask was provided,
        # otherwise use the full field.
        if mask is not None and mask.shape == data.shape:
            active = data[mask > 0]
        else:
            active = data.ravel()

        src_min = float(active.min()) if active.size > 0 else float(data.min())
        src_max = float(active.max()) if active.size > 0 else float(data.max())

        span = src_max - src_min
        if span == 0.0:
            # Flat field: fill with low.
            result = np.full_like(data, low)
        else:
            result = low + (data - src_min) / span * (high - low)

        # field.replace() copies all metadata (size, units, offsets) and
        # substitutes a new data array.  Always use this instead of building
        # a DataField from scratch, so physical dimensions are preserved.

        # Build a RECORD_TABLE: a list of {"quantity", "value", "unit"} dicts.
        # Use field.si_unit_z for the physical Z unit stored on the field
        # (e.g. "m" for height data).  Plain dimensionless numbers get "".
        table = RecordTable([
            {"quantity": "Source min",  "value": src_min,        "unit": field.si_unit_z},
            {"quantity": "Source max",  "value": src_max,        "unit": field.si_unit_z},
            {"quantity": "Source span", "value": src_max - src_min, "unit": field.si_unit_z},
            {"quantity": "Output low",  "value": low,            "unit": ""},
            {"quantity": "Output high", "value": high,           "unit": ""},
        ])

        # Return one value per OUTPUTS entry, in the same order.
        return (field.replace(data=result), table)
