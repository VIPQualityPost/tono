"""
Central Add Node menu manifest.

Edit MENU_LAYOUT to rearrange which nodes appear under each menu leaf and
their order within that leaf. Node classes not listed here fall back to their
class CATEGORY.
"""

from __future__ import annotations

from typing import Any


MENU_LAYOUT: dict[str, list[str]] = {
    "Add": [
        "Image",
        "ImageDemo",
        "Folder",
        "ColorMap",
        "Number",
        "RangeSlider",
        "Coordinate",
        "CoordinatePair",
        "Font",
    ],
    "Output": [
        "PreviewImage",
        "SaveImage",
        "View3D",
        "PrintTable",
        "ValueDisplay",
    ],
    "Overlay": [
        "Markup",
        "Annotations",
    ],
    "Modify": [
        "ColormapAdjust",
        "CropResizeField",
        "RotateField",
    ],
    "Filter": [
        "GaussianFilter",
        "MedianFilter",
        "EdgeDetect",
        "FFTFilter1D",
        "FFTFilter2D",
    ],
    "Frequency": [
        "FFT2D",
        "InverseFFT2D",
    ],
    "Flatten": [
        "PlaneLevelField",
        "PolyLevelField",
        "FixZero",
    ],
    "Measure": [
        "CrossSection",
        "Histogram",
        "Cursors",
        "Statistics",
        "Stats",
    ],
    "Mask": [
        "DrawMask",
        "ThresholdMask",
        "MaskMorphology",
        "MaskInvert",
        "MaskCombine",
    ],
    "Particles": [
        "ParticleAnalysis",
    ],
}


_CATEGORY_ORDER = {category: index for index, category in enumerate(MENU_LAYOUT)}
_NODE_METADATA: dict[str, dict[str, Any]] = {}
for category, class_names in MENU_LAYOUT.items():
    for node_order, class_name in enumerate(class_names):
        _NODE_METADATA[class_name] = {
            "category": category,
            "category_order": _CATEGORY_ORDER[category],
            "menu_order": node_order,
        }


def get_menu_metadata(class_name: str) -> dict[str, Any]:
    metadata = _NODE_METADATA.get(class_name)
    if metadata is not None:
        return dict(metadata)

    return {
        "category": "Unsorted",
        "category_order": len(_CATEGORY_ORDER),
        "menu_order": 10_000,
    }
