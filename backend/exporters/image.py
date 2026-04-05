"""
Exporter for IMAGE values (numpy arrays, ImageData annotation sources).

Images are raw pixel arrays — no physical calibration by design — so none of
the formats here round-trip dimensions. PNG/TIFF convert to uint8 via the
same image_to_uint8 helper the preview pipeline uses; NPZ preserves the raw
array.

Multi-layer stacks are supported for TIFF (multi-page uint8) and NPZ (one
named array per layer). PNG is single-layer only and raises if extra layers
are connected.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from backend.data_types import image_to_uint8
from backend.exporters._base import FormatSpec

accepted_types: tuple[str, ...] = ("IMAGE", "ANNOTATION_SOURCE")

FORMATS: dict[str, FormatSpec] = {
    "PNG":  FormatSpec(ext=".png",  round_trip=False, label="PNG"),
    "TIFF": FormatSpec(ext=".tiff", round_trip=False, label="TIFF"),
    "NPZ":  FormatSpec(ext=".npz",  round_trip=False, label="NumPy (.npz)"),
}

_SINGLE_LAYER_ONLY: frozenset[str] = frozenset({"PNG"})


def save(
    path: Path,
    value: np.ndarray,
    format_name: str,
    *,
    extra_layers: Sequence[Any] | None = None,
    layer_names: Sequence[str] | None = None,
    **_opts,
) -> None:
    extras = list(extra_layers or [])
    layers: list[Any] = [value, *extras]
    names = _resolve_layer_names(len(layers), layer_names, default_primary=path.stem or "image")

    if extras and format_name in _SINGLE_LAYER_ONLY:
        raise ValueError(
            f"{format_name} only supports a single layer. Use 'TIFF' or 'NPZ' "
            f"for multi-layer image saves."
        )

    if format_name == "PNG":
        from PIL import Image
        Image.fromarray(image_to_uint8(np.asarray(value))).save(str(path))
        return
    if format_name == "TIFF":
        _save_tiff(path, layers, names)
        return
    if format_name == "NPZ":
        _save_npz(path, layers, names)
        return
    raise ValueError(f"Format {format_name!r} is not supported for IMAGE.")


def _save_tiff(path: Path, layers: Sequence[Any], names: Sequence[str]) -> None:
    import tifffile

    if len(layers) == 1:
        tifffile.imwrite(str(path), image_to_uint8(np.asarray(layers[0])))
        return
    with tifffile.TiffWriter(str(path)) as tif:
        for layer, layer_name in zip(layers, names):
            tif.write(image_to_uint8(np.asarray(layer)), description=layer_name)


def _save_npz(path: Path, layers: Sequence[Any], names: Sequence[str]) -> None:
    if len(layers) == 1:
        # Preserve the single-layer key used by the legacy test suite.
        np.savez(str(path), image=np.asarray(layers[0]))
        return
    raw_keys = [_safe_identifier(name, i) for i, name in enumerate(names)]
    keys = _dedupe_keys(raw_keys)
    arrays = {key: np.asarray(layer) for key, layer in zip(keys, layers)}
    np.savez(str(path), **arrays)


def _resolve_layer_names(
    count: int,
    raw_names: Sequence[str] | None,
    *,
    default_primary: str,
) -> list[str]:
    raw_names = list(raw_names or [])
    out: list[str] = []
    for i in range(count):
        raw = str(raw_names[i]).strip() if i < len(raw_names) and raw_names[i] is not None else ""
        if raw:
            out.append(raw)
        elif i == 0:
            out.append(default_primary)
        else:
            out.append(f"layer_{i + 1}")
    return out


def _safe_identifier(name: str, index: int) -> str:
    key = re.sub(r"[^0-9A-Za-z_]+", "_", str(name).strip()).strip("_")
    if not key:
        key = f"layer_{index + 1}"
    if key[0].isdigit():
        key = f"layer_{key}"
    return key


def _dedupe_keys(raw_keys: Sequence[str]) -> list[str]:
    used: set[str] = set()
    result: list[str] = []
    for k in raw_keys:
        candidate = k
        suffix = 2
        while candidate in used:
            candidate = f"{k}_{suffix}"
            suffix += 1
        used.add(candidate)
        result.append(candidate)
    return result
