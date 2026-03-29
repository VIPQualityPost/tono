"""
Central Add Node menu manifest.

Edit MENU_LAYOUT to rearrange which nodes appear under each menu leaf and
their order within that leaf. Node classes not listed here fall back to their
class CATEGORY.
"""

from __future__ import annotations

from typing import Any


MENU_LAYOUT: dict[str, list[str]] = {
    "Input": [
        "Image",
        "Note",
        "ImageDemo",
        "Folder",
        "Number",
        "RangeSlider",
        "Coordinate",
        "CoordinatePair",
    ],
    "Display": [
        "ColorMap",
        "Font",
        "ColormapAdjust",
        "PreviewImage",
        "ValueDisplay",
        "View3D",
        "Save",
        "SaveImage",
        "PrintTable",
    ],
    "Overlay": [
        "Markup",
        "Annotations",
        "AngleMeasure",
    ],
    "Geometry": [
        "CropResizeField",
        "RotateField",
        "FlipField",
    ],
    "Filter": [
        "GaussianFilter",
        "MedianFilter",
        "EdgeDetect",
        "FFTFilter1D",
        "FFTFilter2D",
        "ScarRemoval",
    ],
    "Spectral": [
        "FFT2D",
        "FFT2DInverse",
        "FFTFilter1D",
        "FFTFilter2D",
        "ACF2D",
        "ACF1D",
        "PSDF",
    ],
    "Level & Correct": [
        "FixZero",
        "PlaneLevelField",
        "PolyLevelField",
        "FacetLevelField",
        "LineCorrection",
        "ScarRemoval",
    ],
    "Measure": [
        "FFT1D",
        "AngleMeasure",
        "CrossSection",
        "Histogram",
        "Cursors",
        "Curvature",
        "FractalDimension",
        "ACF2D",
        "ACF1D",
        "PSDF",
        "Statistics",
        "Stats",
    ],
    "Mask": [
        "DrawMask",
        "ThresholdMask",
        "MaskMorphology",
        "MaskInvert",
        "MaskOperations",
        "GrainDistanceTransform",
        "WatershedSegmentation",
    ],
    "Grains": [
        "GrainDistanceTransform",
        "WatershedSegmentation",
        "GrainAnalysis",
    ],
}


_CATEGORY_ORDER = {category: index for index, category in enumerate(MENU_LAYOUT)}
_NODE_METADATA: dict[str, dict[str, Any]] = {}
for category, class_names in MENU_LAYOUT.items():
    for node_order, class_name in enumerate(class_names):
        metadata = _NODE_METADATA.setdefault(class_name, {
            "category": category,
            "category_order": _CATEGORY_ORDER[category],
            "menu_order": node_order,
            "menu_categories": [],
        })
        metadata["menu_categories"].append({
            "category": category,
            "category_order": _CATEGORY_ORDER[category],
            "menu_order": node_order,
        })


def get_menu_metadata(class_name: str) -> dict[str, Any]:
    metadata = _NODE_METADATA.get(class_name)
    if metadata is not None:
        return dict(metadata)

    return {
        "category": "Unsorted",
        "category_order": len(_CATEGORY_ORDER),
        "menu_order": 10_000,
        "menu_categories": [{
            "category": "Unsorted",
            "category_order": len(_CATEGORY_ORDER),
            "menu_order": 10_000,
        }],
    }
