"""
Graph execution engine for argonode.

Prompt format (same as ComfyUI):
    {
        "node_id": {
            "class_type": "GaussianFilter",
            "inputs": {
                "field": ["upstream_node_id", 0],   # link: [src_id, output_slot]
                "sigma": 2.0                          # constant widget value
            }
        },
        ...
    }

The engine:
1. Topologically sorts nodes (Kahn's algorithm).
2. Resolves input links to actual Python objects from earlier outputs.
3. Calls each node's FUNCTION method.
4. Emits progress callbacks after each node.
"""

from __future__ import annotations
import uuid
from collections import defaultdict, deque
from math import isfinite
from time import perf_counter
from typing import Any, Callable

from backend.node_registry import NODE_CLASS_MAPPINGS


def _is_link(value: Any) -> bool:
    """A value is a link if it's a [node_id_str, slot_int] pair."""
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], int)
    )


class ExecutionEngine:
    """Synchronous (blocking) graph executor. Run inside a thread pool from async code."""

    def execute(
        self,
        prompt: dict[str, dict],
        on_node_start: Callable[[str], None] | None = None,
        on_node_done: Callable[[str, float], None] | None = None,
        on_preview: Callable[[str, str], None] | None = None,
        on_table: Callable[[str, list], None] | None = None,
        on_mesh: Callable[[str, dict], None] | None = None,
        on_overlay: Callable[[str, str], None] | None = None,
        on_value: Callable[[str, Any], None] | None = None,
        on_warning: Callable[[str, str], None] | None = None,
    ) -> dict[str, tuple]:
        """
        Execute the workflow described by `prompt`.

        Parameters
        ----------
        prompt          : workflow dict (node_id → {class_type, inputs})
        on_node_start   : called with node_id just before a node executes
        on_node_done    : called with (node_id, elapsed_ms) just after a node executes
        on_preview      : called with (node_id, data_uri) when a display node runs
        on_table        : called with (node_id, table_list) when PrintTable runs
        on_overlay      : called with (node_id, data_uri) for interactive overlays
        on_value        : called with (node_id, scalar-payload) for scalar displays
        on_warning      : called with (node_id, message) for node warnings

        Returns
        -------
        node_outputs    : {node_id → tuple-of-outputs} for every executed node
        """
        order = self._topological_sort(prompt)
        node_outputs: dict[str, tuple] = {}

        # Inject display callbacks before execution
        self._inject_display_callbacks(on_preview, on_table, on_mesh, on_overlay, on_value, on_warning)

        for node_id in order:
            node_def = prompt[node_id]
            class_name = node_def["class_type"]

            if class_name not in NODE_CLASS_MAPPINGS:
                raise ValueError(f"Unknown node type: '{class_name}'")

            cls = NODE_CLASS_MAPPINGS[class_name]
            raw_inputs = node_def.get("inputs", {})
            input_types = cls.INPUT_TYPES()
            inputs = self._resolve_inputs(raw_inputs, node_outputs, input_types)

            # Let display nodes know their node_id so they can tag WS messages
            self._set_node_id_on_display(cls, node_id)

            if on_node_start:
                on_node_start(node_id)

            instance = cls()
            func = getattr(instance, cls.FUNCTION)
            start_time = perf_counter()
            result = func(**inputs)
            elapsed_ms = (perf_counter() - start_time) * 1000.0

            # Nodes must return a tuple; coerce single values just in case
            if not isinstance(result, tuple):
                result = (result,)

            node_outputs[node_id] = result

            # Auto-preview: broadcast a thumbnail for any DATA_FIELD,
            # IMAGE, or table-like output so every node shows its result.
            if on_preview or on_table:
                self._auto_preview(cls, node_id, result, on_preview, on_table, inputs)

            if on_node_done:
                on_node_done(node_id, elapsed_ms)

        return node_outputs

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _topological_sort(self, prompt: dict) -> list[str]:
        """Kahn's algorithm — returns node IDs in dependency order."""
        in_degree: dict[str, int] = {nid: 0 for nid in prompt}
        dependents: dict[str, list[str]] = defaultdict(list)

        for node_id, node_def in prompt.items():
            for value in node_def.get("inputs", {}).values():
                if _is_link(value):
                    src_id = value[0]
                    if src_id in prompt:
                        in_degree[node_id] += 1
                        dependents[src_id].append(node_id)

        queue: deque[str] = deque(nid for nid, deg in in_degree.items() if deg == 0)
        order: list[str] = []

        while queue:
            nid = queue.popleft()
            order.append(nid)
            for dep in dependents[nid]:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

        if len(order) != len(prompt):
            raise ValueError("Cycle detected in workflow graph — cannot execute.")

        return order

    def _resolve_inputs(
        self,
        raw_inputs: dict[str, Any],
        node_outputs: dict[str, tuple],
        input_types: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Replace [src_id, slot] links with actual output values."""
        specs = {}
        if input_types:
            specs.update(input_types.get("required", {}))
            specs.update(input_types.get("optional", {}))

        resolved = {}
        for key, value in raw_inputs.items():
            if _is_link(value):
                src_id, slot = value[0], int(value[1])
                if src_id not in node_outputs:
                    raise KeyError(
                        f"Node '{src_id}' has no output yet — dependency ordering bug?"
                    )
                outputs = node_outputs[src_id]
                if slot >= len(outputs):
                    raise IndexError(
                        f"Node '{src_id}' only has {len(outputs)} outputs, "
                        f"but slot {slot} was requested."
                    )
                resolved_value = outputs[slot]
            else:
                resolved_value = value

            resolved[key] = self._coerce_input_value(resolved_value, specs.get(key))
        return resolved

    def _coerce_input_value(self, value: Any, spec: Any) -> Any:
        if spec is None:
            return value

        input_type = spec[0] if isinstance(spec, (list, tuple)) and spec else spec
        if isinstance(input_type, list):
            return value

        if input_type == "INT":
            numeric = float(value)
            if not isfinite(numeric):
                raise ValueError(f"Expected a finite numeric value for INT input, got {value!r}")
            rounded = int(abs(numeric) + 0.5)
            return rounded if numeric >= 0 else -rounded

        if input_type == "FLOAT":
            numeric = float(value)
            if not isfinite(numeric):
                raise ValueError(f"Expected a finite numeric value for FLOAT input, got {value!r}")
            return numeric

        return value

    def _inject_display_callbacks(
        self,
        on_preview: Callable | None,
        on_table: Callable | None,
        on_mesh: Callable | None = None,
        on_overlay: Callable | None = None,
        on_value: Callable | None = None,
        on_warning: Callable | None = None,
    ) -> None:
        """Wire up broadcast callbacks on display node classes."""
        from backend.nodes.preview_image import PreviewImage
        from backend.nodes.print_table import PrintTable
        from backend.nodes.view_3d import View3D
        from backend.nodes.annotations import Annotations
        from backend.nodes.value_display import ValueDisplay
        from backend.nodes.markup import Markup
        from backend.nodes.cross_section import CrossSection
        from backend.nodes.cursors import Cursors
        from backend.nodes.stats import Stats
        from backend.nodes.histogram import Histogram
        from backend.nodes.crop_resize_field import CropResizeField
        from backend.nodes.rotate_field import RotateField
        from backend.nodes.threshold_mask import ThresholdMask
        from backend.nodes.mask_morphology import MaskMorphology
        from backend.nodes.mask_invert import MaskInvert
        from backend.nodes.mask_combine import MaskCombine
        from backend.nodes.draw_mask import DrawMask
        from backend.nodes.save import Save
        from backend.nodes.save_image import SaveImage
        from backend.nodes.image import Image
        from backend.nodes.image_demo import ImageDemo

        PreviewImage._broadcast_fn = on_preview
        ThresholdMask._broadcast_fn = on_preview
        MaskMorphology._broadcast_fn = on_preview
        MaskInvert._broadcast_fn = on_preview
        MaskCombine._broadcast_fn = on_preview
        DrawMask._broadcast_overlay_fn = on_overlay
        View3D._broadcast_mesh_fn = on_mesh
        Annotations._broadcast_warning_fn = on_warning
        PrintTable._broadcast_table_fn = on_table
        ValueDisplay._broadcast_value_fn = on_value
        Stats._broadcast_value_fn = on_value
        Histogram._broadcast_overlay_fn = on_overlay
        CrossSection._broadcast_overlay_fn = on_overlay
        Cursors._broadcast_overlay_fn = on_overlay
        CropResizeField._broadcast_overlay_fn = on_overlay
        RotateField._broadcast_warning_fn = on_warning
        Markup._broadcast_overlay_fn = on_overlay
        Image._broadcast_warning_fn = on_warning
        ImageDemo._broadcast_warning_fn = on_warning
        Save._broadcast_warning_fn = on_warning
        SaveImage._broadcast_warning_fn = on_warning

    def _set_node_id_on_display(self, cls: type, node_id: str) -> None:
        """Inform display nodes of their current node_id for WS tagging."""
        from backend.nodes.preview_image import PreviewImage
        from backend.nodes.print_table import PrintTable
        from backend.nodes.view_3d import View3D
        from backend.nodes.annotations import Annotations
        from backend.nodes.value_display import ValueDisplay
        from backend.nodes.markup import Markup
        from backend.nodes.cross_section import CrossSection
        from backend.nodes.cursors import Cursors
        from backend.nodes.stats import Stats
        from backend.nodes.histogram import Histogram
        from backend.nodes.crop_resize_field import CropResizeField
        from backend.nodes.rotate_field import RotateField
        from backend.nodes.threshold_mask import ThresholdMask
        from backend.nodes.mask_morphology import MaskMorphology
        from backend.nodes.mask_invert import MaskInvert
        from backend.nodes.mask_combine import MaskCombine
        from backend.nodes.draw_mask import DrawMask
        from backend.nodes.image import Image
        from backend.nodes.image_demo import ImageDemo
        from backend.nodes.save import Save
        from backend.nodes.save_image import SaveImage
        if cls in (PreviewImage, PrintTable, View3D, Annotations, ValueDisplay, Stats, Histogram, CrossSection, Cursors, CropResizeField, RotateField, Markup,
                   ThresholdMask, MaskMorphology, MaskInvert, MaskCombine, DrawMask,
                   Image, ImageDemo, Save, SaveImage):
            cls._current_node_id = node_id

    def _auto_preview(
        self,
        cls: type,
        node_id: str,
        result: tuple,
        on_preview: Callable | None,
        on_table: Callable | None,
        inputs: dict[str, Any] | None = None,
    ) -> None:
        """
        After every node executes, inspect its outputs and broadcast
        a preview for the first DATA_FIELD, IMAGE, or table-like output found.
        Skip nodes that broadcast their own custom preview.
        """
        import numpy as np
        from backend.data_types import (
            DataField, LineData, image_to_uint8, encode_preview, render_datafield_preview,
        )
        from backend.nodes.image import Image
        from backend.nodes.image_demo import ImageDemo

        if getattr(cls, "_CUSTOM_PREVIEW", False):
            return

        if cls in (Image, ImageDemo) and on_preview:
            preview = self._render_load_node_preview(result, inputs or {})
            if preview:
                on_preview(node_id, preview)
                return

        return_types = getattr(cls, "RETURN_TYPES", ())

        for slot, type_name in enumerate(return_types):
            if slot >= len(result):
                break
            value = result[slot]

            if type_name == "DATA_FIELD" and isinstance(value, DataField) and on_preview:
                arr = render_datafield_preview(value, value.colormap)
                on_preview(node_id, encode_preview(arr))
                return  # one preview per node is enough

            if type_name == "IMAGE" and isinstance(value, np.ndarray) and on_preview:
                arr = image_to_uint8(value)
                on_preview(node_id, encode_preview(arr))
                return

            if type_name == "ANNOTATION_SOURCE" and on_preview:
                if isinstance(value, DataField):
                    arr = render_datafield_preview(value, value.colormap)
                    on_preview(node_id, encode_preview(arr))
                    return
                if isinstance(value, np.ndarray):
                    arr = image_to_uint8(value)
                    on_preview(node_id, encode_preview(arr))
                    return

            if type_name == "LINE" and isinstance(value, (np.ndarray, LineData)) and on_preview:
                preview = self._render_line_preview(cls, slot, result)
                if preview:
                    on_preview(node_id, preview)
                    return

            if type_name in ("TABLE", "MEASURE_TABLE", "RECORD_TABLE") and isinstance(value, list) and on_table:
                on_table(node_id, value)
                return

    def _render_load_node_preview(
        self,
        result: tuple,
        inputs: dict[str, Any],
    ) -> dict | None:
        from backend.data_types import DataField, encode_preview, render_datafield_preview
        from backend.nodes.helpers import list_channels

        fields = [value for value in result if isinstance(value, DataField)]
        if not fields:
            return None

        selected_path = str(inputs.get("path") or inputs.get("filename") or inputs.get("name") or "").strip()
        channel_names: list[str] = []
        if selected_path:
            try:
                channel_names = [str(entry.get("name", "")).strip() or "field" for entry in list_channels(selected_path)]
            except Exception:
                channel_names = []

        layers = []
        for index, field in enumerate(fields):
            arr = render_datafield_preview(field, field.colormap)
            layers.append({
                "name": channel_names[index] if index < len(channel_names) else f"layer {index + 1}",
                "image": encode_preview(arr),
            })

        return {
            "kind": "layer_gallery",
            "layers": layers,
        }


    def _render_line_preview(
        self,
        cls: type,
        slot: int,
        result: tuple,
    ) -> dict | None:
        """Return structured LINE preview data for responsive frontend rendering."""
        import numpy as np
        from backend.data_types import LineData

        return_types = getattr(cls, "RETURN_TYPES", ())

        # Find the y-values (current slot) and try to find an x-axis
        y = result[slot]
        x = None
        # If the next output is also LINE, use it as x-axis
        if slot + 1 < len(return_types) and return_types[slot + 1] == "LINE":
            x = result[slot + 1]
        # Or if slot > 0 and previous is LINE, this slot is the x-axis — skip
        if slot > 0 and return_types[slot - 1] == "LINE":
            return None  # the first LINE already plotted both

        try:
            import base64
            import io as _io
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            y_meta = y if isinstance(y, LineData) else None
            y = np.asarray(y, dtype=np.float64).ravel()
            if x is None and y_meta is not None and y_meta.x_axis is not None:
                x = y_meta.x_axis
            if x is None:
                x = np.arange(len(y), dtype=np.float64)
            else:
                x = np.asarray(x, dtype=np.float64).ravel()[:len(y)]

            fig, ax = plt.subplots(figsize=(3.2, 1.8), dpi=100)
            fig.patch.set_facecolor("#1e293b")
            ax.set_facecolor("#0f172a")
            ax.plot(x, y, color="#ff9800", linewidth=1.2)
            ax.tick_params(colors="#94a3b8", labelsize=7)
            for spine in ax.spines.values():
                spine.set_color("#334155")
            ax.grid(True, color="#334155", linewidth=0.3, alpha=0.5)
            fig.tight_layout(pad=0.4)

            buf = _io.BytesIO()
            fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
            plt.close(fig)
            fallback_image = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

            return {
                "kind": "line_plot",
                "line": y.tolist(),
                "x_axis": x.tolist(),
                "interactive": False,
                "fallback_image": fallback_image,
            }
        except Exception:
            return None


def new_prompt_id() -> str:
    return str(uuid.uuid4())
