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
        "ImageDemo",        
        "Folder",
        "SyntheticSurface",
        "Note",
        "TextNote",
        "Number",
        "RangeSlider",
        "Coordinate",
        "CoordinatePair",
    ],
    "Display": [
        "PreviewImage",
        "View3D",
        "ColorMap",
        "ColormapAdjust",
        "Font",
        "ValueIO",
        "PrintTable",
        "Save",
        "SaveImage",
        "Shade",
        "PresentationOps",
    ],
    "Overlay": [
        "Markup",
        "Annotations",
        "AngleMeasure",
        "Cursors",
    ],
    "Geometry": [
        "CropResizeField",
        "RotateField",
        "FlipField",
        "Resample",
        "AffineCorrection",
        "PerspectiveCorrection",
        "PolynomialDistortion",
        "ImageStitch",
        "MutualCrop",
        "ImmerseDetail",
        "PixelBinning",
        "ExtendPad",
        "FieldArithmetic",
        "DisplacementField",
    ],
    "Level & Correct": [
        "FixZero",
        "PlaneLevelField",
        "PolyLevelField",
        "FacetLevelField",
        "FlattenBase",
        "LineCorrection",
        "DriftCorrection",
        "ScarRemoval",
        "SpotRemoval",
        "LaplaceInterpolation",
        "FractalInterpolation",
        "ScanLineReorder",
        "Tilt",
        "WrapValue",
        "DistributionCoercion",
        "Calibration",
    ],
    "Filter": [
        "GaussianFilter",
        "MedianFilter",
        "KuwaharaFilter",
        "WaveletDenoise",
        "LocalContrast",
        "CustomConvolution",
        "Deconvolution",
        "MedianBackground",
        "TrimmedMean",
        "RankFilter",
        "Gradient",
        "EdgeDetect",
    ],
    "Spectral": [
        "FFT2D",
        "FFT2DInverse",
        "FFTFilter",
        "FFT1D",
        "ACF2D",
        "ACF1D",
        "PSDF",
        "LogPolarPSDF",
        "FrequencySplit",
        "CrossCorrelate",
        "SuperResolution",
    ],
    "Measure": [
        "CrossSection",
        "Histogram",
        "Statistics",
        "Stats",
        "Curvature",
        "ShapeFitting",
        "TerraceFit",
        "FractalDimension",
        "Entropy",
        "SlopeDistribution",
        "RadialProfile",
        "LatticeMeasurement",
        "AngleMeasure",
        "MultipleProfiles",
        "StraightenPath",
        "RelateFields",
        "DWTAnisotropy",
    ],
    "Detect": [
        "FeatureDetection",
        "HoughTransform",
        "TemplateMatch",
        "FacetAnalysis",
        "MFMAnalysis",
        "MFMCurrentSimulation",
        "MFMDomainGeneration",
        "ZeroCrossing",
        "PFMAnalysis",
        "LateralForceSim",
        "SEMSimulation",
        "SMMAnalysis",
        "PixelClassification",
        "NeuralClassification",
        "LogisticClassification",
    ],
    "Mask": [
        "DrawMask",
        "ThresholdMask",
        "GrainMark",
        "OutlierMask",
        "MaskMorphology",
        "MaskInvert",
        "MaskOperations",
        "MarkDisconnected",
        "MaskShift",
        "MaskNoisify",
    ],
    "Grains": [
        "GrainDistanceTransform",
        "WatershedSegmentation",
        "GrainAnalysis",
        "GrainFilter",
        "GrainDistributions",
        "GrainSummary",
        "LevelGrains",
        "GrainEdge",
        "GrainCross",
        "GrainVisualization",
    ],
    "Tip": [
        "TipModel",
        "TipDeconvolution",
        "BlindTipEstimate",
        "TipShapeEstimate",
        "PSFEstimation",
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


def get_menu_metadata(class_name: str, cls: type | None = None) -> dict[str, Any]:
    metadata = _NODE_METADATA.get(class_name)
    if metadata is not None:
        return dict(metadata)

    # Nodes not listed in MENU_LAYOUT (e.g. plugins) can declare their own
    # menu category via a CATEGORY class attribute.  Falls back to "Unsorted".
    category = getattr(cls, "CATEGORY", "Unsorted") if cls else "Unsorted"
    order = len(_CATEGORY_ORDER)
    return {
        "category": category,
        "category_order": order,
        "menu_order": 10_000,
        "menu_categories": [{
            "category": category,
            "category_order": order,
            "menu_order": 10_000,
        }],
    }
