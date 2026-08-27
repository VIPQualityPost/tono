"""
Graph execution engine for tono.

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
import hashlib
import json
import uuid
from copy import deepcopy
from collections import OrderedDict, defaultdict, deque
from math import isfinite
from threading import RLock
from time import perf_counter
from typing import Any, Callable

from backend.node_registry import NODE_CLASS_MAPPINGS, get_node_output_types, get_node_output_accepted_types
from backend.execution_context import active_node, execution_callbacks


def _is_link(value: Any) -> bool:
    """A value is a link if it's a [node_id_str, slot_int] pair."""
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], int)
    )


# Input kinds that resolve to filesystem paths. Nodes consuming these are
# excluded from the engine result cache — the file loaders keep their own
# (path, mtime, size) cache, so identical re-runs stay fast while replaced
# files or changed folder contents always produce fresh results.
_PATH_INPUT_KINDS = frozenset({"FILE_PICKER", "FILE_PATH", "FOLDER_PICKER", "DIRECTORY"})


def get_cacheability(cls: type) -> bool:
    """Return whether a node class may be served from the persistent result cache."""
    if getattr(cls, "MANUAL_TRIGGER", False):
        # Manual triggers (e.g. Save) must re-run on every identical submission;
        # caching them turned repeated clicks into silent no-ops.
        return False
    try:
        input_types = cls.INPUT_TYPES()
    except Exception:
        return True
    specs: dict[str, Any] = {}
    if isinstance(input_types, dict):
        specs.update(input_types.get("required", {}) or {})
        specs.update(input_types.get("optional", {}) or {})
    for spec in specs.values():
        kind = spec[0] if isinstance(spec, (list, tuple)) and spec else None
        if isinstance(kind, str) and kind in _PATH_INPUT_KINDS:
            return False
    return True


_SOCKET_TYPE_CHECKS: dict[str, type | tuple[type, ...]] = {}


def _socket_type_matches(type_name: str, value: Any) -> bool:
    """Return whether *value* is a runtime instance of the type a socket name denotes."""
    check = _SOCKET_TYPE_CHECKS.get(type_name)
    if check is None:
        from backend.data_types import (
            DataField, DataTable, ImageData, LineData, MeshModel, RecordTable,
        )
        import numpy as np

        if type_name == "DATA_FIELD":
            check = DataField
        elif type_name == "RECORD_TABLE":
            check = RecordTable
        elif type_name == "DATA_TABLE":
            check = DataTable
        elif type_name == "LINE":
            check = LineData
        elif type_name == "IMAGE":
            check = (ImageData, np.ndarray)
        elif type_name == "ANNOTATION_SOURCE":
            check = (DataField, ImageData, np.ndarray)
        elif type_name == "MESH_MODEL":
            check = MeshModel
        else:
            return False
        _SOCKET_TYPE_CHECKS[type_name] = check
    return isinstance(value, check)


def coerce_input_value(value: Any, spec: Any, name: str = "value") -> Any:
    """Coerce a raw widget value into the declared input type.

    INT/FLOAT inputs become int/float and non-finite numerics are rejected;
    on garbage we raise naming the input instead of passing it through to the
    node, where the failure would be deep and hard to attribute. Inputs that
    declare ``accepted_types`` (polymorphic sockets) still receive values of a
    matching socket type unchanged — e.g. a FLOAT socket that also accepts
    RECORD_TABLE is handed the linked table, not rejected.
    """
    if spec is None:
        return value

    input_type = spec[0] if isinstance(spec, (list, tuple)) and spec else spec
    if isinstance(input_type, list):
        return value

    if input_type in ("INT", "FLOAT"):
        accepted_types = (
            spec[1].get("accepted_types") or []
            if isinstance(spec, (list, tuple)) and len(spec) > 1 and isinstance(spec[1], dict)
            else []
        )
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            if any(_socket_type_matches(accepted, value) for accepted in accepted_types):
                return value
            raise ValueError(
                f"Expected a numeric value for {input_type} input '{name}', got {value!r}"
            ) from None
        if not isfinite(numeric):
            raise ValueError(
                f"Expected a finite numeric value for {input_type} input '{name}', got {value!r}"
            )
        if input_type == "INT":
            rounded = int(abs(numeric) + 0.5)
            return rounded if numeric >= 0 else -rounded
        return numeric

    return value


class NodeExecutionError(Exception):
    """Wraps an error that occurred while executing a specific node."""
    def __init__(self, node_id: str, original: Exception):
        self.node_id = node_id
        super().__init__(str(original))


class ExecutionEngine:
    """Synchronous (blocking) graph executor. Run inside a thread pool from async code."""

    NODE_CACHE_LIMIT = 256

    def __init__(self) -> None:
        self._node_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._cache_lock = RLock()
        self._cache_warning_emitted = False

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
        on_file_download: Callable[[str, str], None] | None = None,
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
        node_output_signatures: dict[str, tuple[str, ...]] = {}

        with execution_callbacks(
            preview=on_preview,
            table=on_table,
            mesh=on_mesh,
            overlay=on_overlay,
            value=on_value,
            warning=on_warning,
            file_download=on_file_download,
        ):
            for node_id in order:
                node_def = prompt[node_id]
                class_name = node_def["class_type"]

                if class_name not in NODE_CLASS_MAPPINGS:
                    raise NodeExecutionError(node_id, ValueError(f"Unknown node type: '{class_name}'"))

                cls = NODE_CLASS_MAPPINGS[class_name]
                raw_inputs = node_def.get("inputs", {})
                input_types = cls.INPUT_TYPES()
                try:
                    inputs = self._resolve_inputs(raw_inputs, node_outputs, input_types)
                except Exception as exc:
                    raise NodeExecutionError(node_id, exc) from exc
                input_signature = self._build_input_signature(class_name, raw_inputs, node_output_signatures)

                cache_entry = self._get_cached_entry(node_id, class_name, input_signature)
                if cache_entry is not None:
                    result = self._clone_cached_outputs(cache_entry["outputs"])
                    elapsed_ms = 0.0
                else:
                    if on_node_start:
                        on_node_start(node_id)

                    instance = cls()
                    func = getattr(instance, cls.FUNCTION)
                    start_time = perf_counter()
                    try:
                        with active_node(node_id):
                            result = func(**inputs)
                    except NodeExecutionError:
                        raise
                    except Exception as exc:
                        raise NodeExecutionError(node_id, exc) from exc
                    elapsed_ms = (perf_counter() - start_time) * 1000.0

                # Nodes must return a tuple; coerce single values just in case
                if not isinstance(result, tuple):
                    result = (result,)

                node_outputs[node_id] = result
                output_signatures = tuple(self._fingerprint_value(value) for value in result)
                node_output_signatures[node_id] = output_signatures

                if cache_entry is None and self._node_cacheable(cls):
                    self._store_cache_entry(
                        node_id=node_id,
                        class_name=class_name,
                        input_signature=input_signature,
                        output_signatures=output_signatures,
                        outputs=self._clone_cached_outputs(result),
                        on_warning=on_warning,
                    )

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
                        f"Input '{key}' references node '{src_id}', which produced no "
                        f"output (missing from the workflow, deleted, or failed upstream)."
                    )
                outputs = node_outputs[src_id]
                if slot < 0 or slot >= len(outputs):
                    raise IndexError(
                        f"Node '{src_id}' only has {len(outputs)} outputs, "
                        f"but slot {slot} was requested by input '{key}'."
                    )
                resolved_value = outputs[slot]
            else:
                resolved_value = value

            resolved[key] = coerce_input_value(resolved_value, specs.get(key), name=key)
        return resolved

    def _node_cacheable(self, cls: type) -> bool:
        return get_cacheability(cls)

    def _get_cached_entry(self, node_id: str, class_name: str, input_signature: str) -> dict[str, Any] | None:
        if not self._node_cacheable(NODE_CLASS_MAPPINGS[class_name]):
            return None
        with self._cache_lock:
            entry = self._node_cache.get(node_id)
            if not entry:
                return None
            if entry.get("class_name") != class_name:
                return None
            if entry.get("input_signature") != input_signature:
                return None
            # Move to end for LRU ordering
            self._node_cache.move_to_end(node_id)
            return entry

    def _store_cache_entry(
        self,
        *,
        node_id: str,
        class_name: str,
        input_signature: str,
        output_signatures: tuple[str, ...],
        outputs: tuple,
        on_warning: Callable[[str, str], None] | None = None,
    ) -> None:
        with self._cache_lock:
            if node_id in self._node_cache:
                self._node_cache.move_to_end(node_id)
            self._node_cache[node_id] = {
                "class_name": class_name,
                "input_signature": input_signature,
                "output_signatures": output_signatures,
                "outputs": outputs,
            }
            if len(self._node_cache) > self.NODE_CACHE_LIMIT:
                self._node_cache.popitem(last=False)
                if not self._cache_warning_emitted and on_warning is not None:
                    self._cache_warning_emitted = True
                    on_warning(
                        node_id,
                        f"Node cache exceeded {self.NODE_CACHE_LIMIT} entries — "
                        "oldest cached results are being evicted. "
                        "Very large workflows may re-compute nodes that would otherwise be cached.",
                    )

    def _build_input_signature(
        self,
        class_name: str,
        raw_inputs: dict[str, Any],
        node_output_signatures: dict[str, tuple[str, ...]],
    ) -> str:
        normalized_inputs: dict[str, Any] = {}
        for key in sorted(raw_inputs):
            value = raw_inputs[key]
            if _is_link(value):
                src_id, slot = value[0], int(value[1])
                source_signatures = node_output_signatures.get(src_id)
                if source_signatures is None:
                    raise KeyError(f"Node '{src_id}' has no output signature yet — dependency ordering bug?")
                if slot < 0 or slot >= len(source_signatures):
                    raise IndexError(
                        f"Node '{src_id}' only has {len(source_signatures)} output signatures, "
                        f"but slot {slot} was requested."
                    )
                normalized_inputs[key] = {
                    "kind": "link",
                    "source": src_id,
                    "slot": slot,
                    "signature": source_signatures[slot],
                }
            else:
                normalized_inputs[key] = {
                    "kind": "value",
                    "signature": self._fingerprint_value(value),
                }

        return self._fingerprint_value({
            "class_type": class_name,
            "inputs": normalized_inputs,
        })

    def _fingerprint_value(self, value: Any) -> str:
        return hashlib.blake2b(self._fingerprint_bytes(value), digest_size=16).hexdigest()

    def _fingerprint_bytes(self, value: Any) -> bytes:
        import numpy as np
        from backend.data_types import DataField, ImageData, LineData, RecordTable, MeshModel, DataTable

        if value is None:
            return b"null"
        if isinstance(value, bool):
            return b"bool:1" if value else b"bool:0"
        if isinstance(value, int) and not isinstance(value, bool):
            return f"int:{value}".encode()
        if isinstance(value, float):
            return json.dumps(float(value), sort_keys=True, separators=(",", ":")).encode()
        if isinstance(value, str):
            return ("str:" + value).encode("utf-8", errors="surrogatepass")

        if isinstance(value, DataField):
            return b"|".join([
                b"DataField",
                self._fingerprint_bytes(value.data),
                f"xreal:{value.xreal}".encode(),
                f"yreal:{value.yreal}".encode(),
                f"xoff:{value.xoff}".encode(),
                f"yoff:{value.yoff}".encode(),
                ("ux:" + value.si_unit_xy).encode(),
                ("uz:" + value.si_unit_z).encode(),
                ("domain:" + value.domain).encode(),
                self._fingerprint_bytes(value.colormap),
                f"display_offset:{value.display_offset}".encode(),
                f"display_scale:{value.display_scale}".encode(),
                self._fingerprint_bytes(value.overlays),
            ])

        if isinstance(value, LineData):
            return b"|".join([
                b"LineData",
                self._fingerprint_bytes(value.data),
                self._fingerprint_bytes(value.x_axis.tolist() if value.x_axis is not None else None),
                ("x_unit:" + value.x_unit).encode(),
                ("y_unit:" + value.y_unit).encode(),
            ])

        if isinstance(value, MeshModel):
            return b"|".join([
                b"MeshModel",
                self._fingerprint_bytes(value.vertices),
                self._fingerprint_bytes(value.faces),
                self._fingerprint_bytes(value.colors if value.colors is not None else None),
            ])

        if isinstance(value, ImageData):
            return b"|".join([
                b"ImageData",
                self._fingerprint_bytes(np.asarray(value)),
                self._fingerprint_bytes(getattr(value, "metadata", {})),
            ])

        if isinstance(value, np.ndarray):
            array = np.ascontiguousarray(value)
            header = json.dumps(
                {"dtype": str(array.dtype), "shape": list(array.shape)},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            return b"|".join([b"ndarray", header, memoryview(array).tobytes()])

        if isinstance(value, (RecordTable, DataTable, list)):
            return b"[" + b",".join(self._fingerprint_bytes(item) for item in value) + b"]"

        if isinstance(value, tuple):
            return b"(" + b",".join(self._fingerprint_bytes(item) for item in value) + b")"

        if isinstance(value, dict):
            items = []
            for key in sorted(value):
                items.append(
                    self._fingerprint_bytes(str(key))
                    + b":"
                    + self._fingerprint_bytes(value[key])
                )
            return b"{" + b",".join(items) + b"}"

        return repr(value).encode("utf-8", errors="surrogatepass")

    def _clone_cached_outputs(self, outputs: tuple) -> tuple:
        return tuple(self._clone_cached_value(value) for value in outputs)

    def _clone_cached_value(self, value: Any) -> Any:
        import numpy as np
        from backend.data_types import DataField, ImageData, LineData, MeshModel

        if isinstance(value, DataField):
            return value.copy()
        if isinstance(value, LineData):
            return LineData(
                data=value.data.copy(),
                x_axis=value.x_axis.copy() if value.x_axis is not None else None,
                x_unit=value.x_unit,
                y_unit=value.y_unit,
            )
        if isinstance(value, MeshModel):
            return MeshModel(
                vertices=value.vertices.copy(),
                faces=value.faces.copy(),
                colors=value.colors.copy() if value.colors is not None else None,
            )
        if isinstance(value, ImageData):
            return value.copy_with_metadata(data=np.asarray(value).copy())
        if isinstance(value, np.ndarray):
            return value.copy()
        if isinstance(value, tuple):
            return tuple(self._clone_cached_value(item) for item in value)
        if isinstance(value, (list, dict)):
            return deepcopy(value)
        return value

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
            preview = self._render_load_node_preview(cls, result, inputs or {})
            if preview:
                on_preview(node_id, preview)
                return

        return_types = get_node_output_types(cls)
        output_accepted = get_node_output_accepted_types(cls)

        for slot, type_name in enumerate(return_types):
            if slot >= len(result):
                break
            value = result[slot]
            all_types = {type_name} | set(output_accepted[slot] if slot < len(output_accepted) else [])

            # For polymorphic outputs, check the actual runtime type first.
            if isinstance(value, DataField) and ("DATA_FIELD" in all_types) and on_preview:
                arr = render_datafield_preview(value, value.colormap)
                on_preview(node_id, encode_preview(arr))
                return

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

            if "LINE" in all_types and isinstance(value, (np.ndarray, LineData)) and on_preview:
                preview = self._render_line_preview(cls, slot, result)
                if preview:
                    on_preview(node_id, preview)
                    return

            if type_name in ("TABLE", "RECORD_TABLE", "DATA_TABLE") and isinstance(value, list) and on_table:
                on_table(node_id, value)
                return

    def _render_load_node_preview(
        self,
        cls: type,
        result: tuple,
        inputs: dict[str, Any],
    ) -> dict | None:
        from backend.data_types import DataField, encode_preview, render_datafield_preview
        from backend.nodes.helpers import list_channels, DEMO_DIR
        from backend.nodes.image_demo import ImageDemo

        fields = [value for value in result if isinstance(value, DataField)]
        if not fields:
            return None

        selected_path = str(inputs.get("path") or inputs.get("filename") or inputs.get("name") or "").strip()
        # ImageDemo passes only the bare demo filename; resolve against DEMO_DIR
        # so list_channels() can find the file and return real channel names.
        if cls is ImageDemo and selected_path:
            selected_path = str(DEMO_DIR / selected_path)
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

        return_types = get_node_output_types(cls)

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
            from PIL import Image, ImageDraw

            y_meta = y if isinstance(y, LineData) else None
            y = np.asarray(y, dtype=np.float64).ravel()
            if x is None and y_meta is not None and y_meta.x_axis is not None:
                x = y_meta.x_axis
            if x is None:
                x = np.arange(len(y), dtype=np.float64)
            else:
                x = np.asarray(x, dtype=np.float64).ravel()[:len(y)]

            # Render a small fallback thumbnail with Pillow
            w, h = 320, 180
            pad = 12
            img = Image.new("RGB", (w, h), (15, 23, 42))  # #0f172a
            draw = ImageDraw.Draw(img)
            n = len(y)
            if n > 1:
                ymin, ymax = float(np.nanmin(y)), float(np.nanmax(y))
                xmin, xmax = float(np.nanmin(x)), float(np.nanmax(x))
                if ymax == ymin:
                    ymin, ymax = ymin - 1, ymax + 1
                if xmax == xmin:
                    xmax = xmin + 1
                pw, ph = w - 2 * pad, h - 2 * pad
                # Downsample if more points than pixels
                step = max(1, n // pw)
                xs = x[::step]
                ys = y[::step]
                pts = [
                    (pad + (float(xs[i]) - xmin) / (xmax - xmin) * pw,
                     pad + (1.0 - (float(ys[i]) - ymin) / (ymax - ymin)) * ph)
                    for i in range(len(xs))
                ]
                draw.line(pts, fill=(255, 152, 0), width=2)  # #ff9800
            buf = _io.BytesIO()
            img.save(buf, format="PNG")
            fallback_image = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

            result_dict = {
                "kind": "line_plot",
                "line": y.tolist(),
                "x_axis": x.tolist(),
                "interactive": False,
                "fallback_image": fallback_image,
            }
            if y_meta is not None and y_meta.x_unit:
                result_dict["x_unit"] = y_meta.x_unit
            return result_dict
        except Exception:
            return None


def new_prompt_id() -> str:
    return str(uuid.uuid4())
