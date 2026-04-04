from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy.ndimage import label

from backend.execution_context import emit_preview
from backend.data_types import DataField, encode_preview
from backend.node_registry import register_node
from backend.nodes.helpers import _mask_overlay, mask_to_bool, bool_to_mask


def _working_height(field: DataField, invert_height: bool) -> np.ndarray:
    data = np.asarray(field.data, dtype=np.float64)
    return -data if invert_height else data.copy()


def _next_indices(data: np.ndarray) -> np.ndarray:
    yres, xres = data.shape
    flat_idx = np.arange(yres * xres, dtype=np.int64).reshape(yres, xres)

    right_val = np.full_like(data, -np.inf, dtype=np.float64)
    right_val[:, :-1] = data[:, 1:]
    left_val = np.full_like(data, -np.inf, dtype=np.float64)
    left_val[:, 1:] = data[:, :-1]
    down_val = np.full_like(data, -np.inf, dtype=np.float64)
    down_val[:-1, :] = data[1:, :]
    up_val = np.full_like(data, -np.inf, dtype=np.float64)
    up_val[1:, :] = data[:-1, :]

    right_idx = flat_idx.copy()
    right_idx[:, :-1] = flat_idx[:, 1:]
    left_idx = flat_idx.copy()
    left_idx[:, 1:] = flat_idx[:, :-1]
    down_idx = flat_idx.copy()
    down_idx[:-1, :] = flat_idx[1:, :]
    up_idx = flat_idx.copy()
    up_idx[1:, :] = flat_idx[:-1, :]

    next_idx = flat_idx.copy()
    local = (
        (data >= right_val)
        & (data >= left_val)
        & (data >= down_val)
        & (data >= up_val)
    )

    right_mask = (~local) & (right_val >= data) & (right_val >= left_val) & (right_val >= down_val) & (right_val >= up_val)
    next_idx[right_mask] = right_idx[right_mask]

    unresolved = (~local) & (~right_mask)
    left_mask = unresolved & (left_val >= data) & (left_val >= right_val) & (left_val >= down_val) & (left_val >= up_val)
    next_idx[left_mask] = left_idx[left_mask]

    unresolved &= ~left_mask
    down_mask = unresolved & (down_val >= data) & (down_val >= right_val) & (down_val >= left_val) & (down_val >= up_val)
    next_idx[down_mask] = down_idx[down_mask]

    unresolved &= ~down_mask
    next_idx[unresolved] = up_idx[unresolved]
    return next_idx.ravel()


def _terminal_indices(data: np.ndarray) -> np.ndarray:
    terminals = _next_indices(np.asarray(data, dtype=np.float64))
    while True:
        jumped = terminals[terminals]
        if np.array_equal(jumped, terminals):
            return terminals
        terminals = jumped


@lru_cache(maxsize=32)
def _source_order(shape: tuple[int, int]) -> np.ndarray:
    yres, xres = shape
    if yres < 3 or xres < 3:
        return np.zeros(0, dtype=np.int64)
    rows, cols = np.mgrid[1:yres - 1, 1:xres - 1]
    order = (rows.ravel(order="F") * xres + cols.ravel(order="F")).astype(np.int64)
    order.setflags(write=False)
    return order


def _location_step(data: np.ndarray, water: np.ndarray, dropsize: float) -> None:
    terminals = _terminal_indices(data)
    ordered_sources = _source_order(data.shape)
    counts = np.bincount(terminals[ordered_sources], minlength=data.size).astype(np.float64)
    water += counts.reshape(data.shape)
    data -= dropsize * counts.reshape(data.shape)


def _seed_labels(water: np.ndarray, threshold: int) -> np.ndarray:
    structure = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.int8)
    labeled, ngrains = label(water > 0.0, structure=structure)
    if ngrains <= 0:
        return np.zeros_like(labeled, dtype=np.int32)

    sizes = np.bincount(labeled.ravel(), minlength=ngrains + 1)
    seeds = np.zeros_like(labeled, dtype=np.int32)
    next_label = 1
    flat_water = water.ravel()
    flat_labeled = labeled.ravel()

    for grain_id in range(1, ngrains + 1):
        if int(sizes[grain_id]) <= int(threshold):
            continue
        indices = np.flatnonzero(flat_labeled == grain_id)
        if indices.size == 0:
            continue
        peak_index = int(indices[np.argmax(flat_water[indices])])
        seeds.ravel()[peak_index] = next_label
        next_label += 1

    return seeds


def _process_mask(labels: np.ndarray, row: int, col: int) -> None:
    yres, xres = labels.shape
    if col == 0 or row == 0 or col == xres - 1 or row == yres - 1:
        labels[row, col] = -1
        return

    if labels[row, col] != 0:
        return

    left = int(labels[row, col - 1])
    up = int(labels[row - 1, col])
    right = int(labels[row, col + 1])
    down = int(labels[row + 1, col])

    if abs(left) + abs(up) + abs(right) + abs(down) == 0:
        return

    value = 0
    boundary = False
    for candidate in (left, up, right, down):
        if value > 0 and candidate > 0 and candidate != value:
            boundary = True
            break
        if candidate > 0:
            value = candidate

    labels[row, col] = -1 if boundary else value


def _watershed_step(
    data: np.ndarray,
    water: np.ndarray,
    labels: np.ndarray,
    seeds: np.ndarray,
    dropsize: float,
) -> None:
    labels[seeds > 0] = seeds[seeds > 0]

    terminals = _terminal_indices(data)
    ordered_sources = _source_order(data.shape)
    ordered_terminals = terminals[ordered_sources]
    xres = data.shape[1]

    for term in ordered_terminals:
        row = int(term // xres)
        col = int(term % xres)
        _process_mask(labels, row, col)

    counts = np.bincount(ordered_terminals, minlength=data.size).astype(np.float64)
    water += counts.reshape(data.shape)
    data -= dropsize * counts.reshape(data.shape)


def _mark_boundaries(labels: np.ndarray) -> np.ndarray:
    result = labels.copy()
    if result.shape[0] < 3 or result.shape[1] < 3:
        return result

    interior = result[1:-1, 1:-1]
    right = result[1:-1, 2:]
    down = result[2:, 1:-1]
    interior[(interior != right) | (interior != down)] = 0
    return result


def _combine_masks(result_mask: np.ndarray, existing_mask: np.ndarray | None, combine_mode: str) -> np.ndarray:
    if existing_mask is None or combine_mode == "replace":
        return result_mask

    existing = mask_to_bool(existing_mask)
    current = np.asarray(result_mask, dtype=bool)
    if existing.shape != current.shape:
        raise ValueError("Existing mask must have the same shape as the watershed output.")

    if combine_mode == "union":
        merged = current | existing
    elif combine_mode == "intersection":
        merged = current & existing
    else:
        raise ValueError(f"Unsupported combine mode: {combine_mode}")

    return bool_to_mask(merged)


@register_node(display_name="Watershed Segmentation")
class WatershedSegmentation:
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "invert_height": ("BOOLEAN", {"default": False}),
                "locate_steps": ("INT", {"default": 10, "min": 1, "max": 200, "step": 1}),
                "locate_threshold": ("INT", {"default": 10, "min": 0, "max": 100000, "step": 1}),
                "locate_drop_size": ("FLOAT", {"default": 0.1, "min": 0.0001, "max": 1.0, "step": 0.01}),
                "watershed_steps": ("INT", {"default": 20, "min": 1, "max": 2000, "step": 1}),
                "watershed_drop_size": ("FLOAT", {"default": 0.1, "min": 0.0001, "max": 1.0, "step": 0.01}),
                "combine_mode": (["replace", "union", "intersection"], {"default": "replace"}),
            },
            "optional": {
                "mask": ("IMAGE",),
            },
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Segment a height field into grains using the two-stage Gwyddion watershed workflow: "
        "drop-based seed location followed by watershed growth. Supports hill or valley detection "
        "and optional union/intersection with an existing mask."
    )

    KEYWORDS = ("grain", "basin", "flood fill", "gwyddion", "peak", "valley", "hill", "marker")

    def process(
        self,
        field: DataField,
        invert_height: bool,
        locate_steps: int,
        locate_threshold: int,
        locate_drop_size: float,
        watershed_steps: int,
        watershed_drop_size: float,
        combine_mode: str,
        mask: np.ndarray | None = None,
    ) -> tuple:
        working = _working_height(field, bool(invert_height))
        water = np.zeros_like(working, dtype=np.float64)

        q = float((np.max(working) - np.min(working)) / 50.0)
        locate_drop = float(locate_drop_size) * q
        watershed_drop = float(watershed_drop_size) * q

        locate_field = working.copy()
        for _ in range(int(locate_steps)):
            _location_step(locate_field, water, locate_drop)

        seeds = _seed_labels(water, int(locate_threshold))
        labels = np.zeros_like(seeds, dtype=np.int32)
        watershed_field = working.copy()
        for _ in range(int(watershed_steps)):
            _watershed_step(watershed_field, water, labels, seeds, watershed_drop)

        labels = _mark_boundaries(labels)
        result_mask = bool_to_mask(labels > 0)
        result_mask = _combine_masks(result_mask, mask, combine_mode)

        emit_preview(encode_preview(_mask_overlay(field, result_mask)))
        return (result_mask,)
