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
        on_node_done: Callable[[str], None] | None = None,
        on_preview: Callable[[str, str], None] | None = None,
        on_table: Callable[[str, list], None] | None = None,
        on_mesh: Callable[[str, dict], None] | None = None,
        on_overlay: Callable[[str, str], None] | None = None,
        on_warning: Callable[[str, str], None] | None = None,
    ) -> dict[str, tuple]:
        """
        Execute the workflow described by `prompt`.

        Parameters
        ----------
        prompt          : workflow dict (node_id → {class_type, inputs})
        on_node_start   : called with node_id just before a node executes
        on_node_done    : called with node_id just after a node executes
        on_preview      : called with (node_id, data_uri) when a display node runs
        on_table        : called with (node_id, table_list) when PrintTable runs
        on_overlay      : called with (node_id, data_uri) for interactive overlays
        on_warning      : called with (node_id, message) for node warnings

        Returns
        -------
        node_outputs    : {node_id → tuple-of-outputs} for every executed node
        """
        order = self._topological_sort(prompt)
        node_outputs: dict[str, tuple] = {}

        # Inject display callbacks before execution
        self._inject_display_callbacks(on_preview, on_table, on_mesh, on_overlay, on_warning)

        for node_id in order:
            node_def = prompt[node_id]
            class_name = node_def["class_type"]

            if class_name not in NODE_CLASS_MAPPINGS:
                raise ValueError(f"Unknown node type: '{class_name}'")

            cls = NODE_CLASS_MAPPINGS[class_name]
            raw_inputs = node_def.get("inputs", {})
            inputs = self._resolve_inputs(raw_inputs, node_outputs)

            # Let display nodes know their node_id so they can tag WS messages
            self._set_node_id_on_display(cls, node_id)

            if on_node_start:
                on_node_start(node_id)

            instance = cls()
            func = getattr(instance, cls.FUNCTION)
            result = func(**inputs)

            # Nodes must return a tuple; coerce single values just in case
            if not isinstance(result, tuple):
                result = (result,)

            node_outputs[node_id] = result

            # Auto-preview: broadcast a thumbnail for any DATA_FIELD,
            # IMAGE, or TABLE output so every node shows its result.
            if on_preview or on_table:
                self._auto_preview(cls, node_id, result, on_preview, on_table)

            if on_node_done:
                on_node_done(node_id)

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
    ) -> dict[str, Any]:
        """Replace [src_id, slot] links with actual output values."""
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
                resolved[key] = outputs[slot]
            else:
                resolved[key] = value
        return resolved

    def _inject_display_callbacks(
        self,
        on_preview: Callable | None,
        on_table: Callable | None,
        on_mesh: Callable | None = None,
        on_overlay: Callable | None = None,
        on_warning: Callable | None = None,
    ) -> None:
        """Wire up broadcast callbacks on display node classes."""
        from backend.nodes.display import PreviewImage, PrintTable, View3D
        from backend.nodes.analysis import CrossSection, LineCursors
        from backend.nodes.mask import ThresholdMask, MaskMorphology, MaskInvert, MaskCombine
        from backend.nodes.io import SaveImage, LoadFile

        PreviewImage._broadcast_fn = on_preview
        ThresholdMask._broadcast_fn = on_preview
        MaskMorphology._broadcast_fn = on_preview
        MaskInvert._broadcast_fn = on_preview
        MaskCombine._broadcast_fn = on_preview
        View3D._broadcast_mesh_fn = on_mesh
        PrintTable._broadcast_table_fn = on_table
        CrossSection._broadcast_overlay_fn = on_overlay
        LineCursors._broadcast_overlay_fn = on_overlay
        LoadFile._broadcast_warning_fn = on_warning
        SaveImage._broadcast_preview = (
            (lambda data_uri: on_preview("save", data_uri)) if on_preview else None
        )

    def _set_node_id_on_display(self, cls: type, node_id: str) -> None:
        """Inform display nodes of their current node_id for WS tagging."""
        from backend.nodes.display import PreviewImage, PrintTable, View3D
        from backend.nodes.analysis import CrossSection, LineCursors
        from backend.nodes.mask import ThresholdMask, MaskMorphology, MaskInvert, MaskCombine
        from backend.nodes.io import LoadFile
        if cls in (PreviewImage, PrintTable, View3D, CrossSection, LineCursors,
                   ThresholdMask, MaskMorphology, MaskInvert, MaskCombine, LoadFile):
            cls._current_node_id = node_id

    def _auto_preview(
        self,
        cls: type,
        node_id: str,
        result: tuple,
        on_preview: Callable | None,
        on_table: Callable | None,
    ) -> None:
        """
        After every node executes, inspect its outputs and broadcast
        a preview for the first DATA_FIELD, IMAGE, or TABLE found.
        Skip nodes that broadcast their own custom preview.
        """
        import numpy as np
        from backend.data_types import (
            DataField, datafield_to_uint8, image_to_uint8, encode_preview,
        )

        if getattr(cls, "_CUSTOM_PREVIEW", False):
            return

        return_types = getattr(cls, "RETURN_TYPES", ())

        for slot, type_name in enumerate(return_types):
            if slot >= len(result):
                break
            value = result[slot]

            if type_name == "DATA_FIELD" and isinstance(value, DataField) and on_preview:
                arr = datafield_to_uint8(value, value.colormap)
                on_preview(node_id, encode_preview(arr))
                return  # one preview per node is enough

            if type_name == "IMAGE" and isinstance(value, np.ndarray) and on_preview:
                arr = image_to_uint8(value)
                on_preview(node_id, encode_preview(arr))
                return

            if type_name == "LINE" and isinstance(value, np.ndarray) and on_preview:
                preview = self._render_line_preview(cls, slot, result)
                if preview:
                    on_preview(node_id, preview)
                    return

            if type_name == "TABLE" and isinstance(value, list) and on_table:
                on_table(node_id, value)
                return


    def _render_line_preview(
        self,
        cls: type,
        slot: int,
        result: tuple,
    ) -> str | None:
        """Render a LINE output as a small matplotlib plot, returned as a data URI."""
        import numpy as np
        import base64
        import io as _io

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
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(3.2, 1.8), dpi=100)
            fig.patch.set_facecolor("#1e293b")
            ax.set_facecolor("#0f172a")
            if x is not None:
                ax.plot(x, y, color="#ff9800", linewidth=1.2)
            else:
                ax.plot(y, color="#ff9800", linewidth=1.2)
            ax.tick_params(colors="#94a3b8", labelsize=7)
            for spine in ax.spines.values():
                spine.set_color("#334155")
            ax.grid(True, color="#334155", linewidth=0.3, alpha=0.5)
            fig.tight_layout(pad=0.4)

            buf = _io.BytesIO()
            fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
            plt.close(fig)
            b64 = base64.b64encode(buf.getvalue()).decode()
            return f"data:image/png;base64,{b64}"
        except Exception:
            return None


def new_prompt_id() -> str:
    return str(uuid.uuid4())
