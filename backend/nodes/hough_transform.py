"""Hough transform — detect lines and circles in images."""

from __future__ import annotations

import numpy as np
from skimage.transform import hough_line, hough_line_peaks, hough_circle, hough_circle_peaks
from skimage.feature import canny

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable


@register_node(display_name="Hough Transform")
class HoughTransform:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "detect": (["lines", "circles"], {"default": "lines"}),
                "n_features": ("INT", {"default": 5, "min": 1, "max": 50}),
                "canny_sigma": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1}),
                "min_radius_px": ("INT", {"default": 10, "min": 2, "max": 500}),
                "max_radius_px": ("INT", {"default": 100, "min": 5, "max": 1000}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'accumulator'),
        ('RECORD_TABLE', 'features'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Detect lines or circles using the Hough transform. "
        "First applies Canny edge detection, then accumulates votes in "
        "Hough parameter space. Reports detected features with their parameters. "
        "For lines: angle and distance from origin. "
        "For circles: centre coordinates and radius. "
    )

    KEYWORDS = ("line detection", "circle detection", "shape detection")

    def process(
        self,
        field: DataField,
        detect: str,
        n_features: int,
        canny_sigma: float,
        min_radius_px: int,
        max_radius_px: int,
    ) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        # Normalise to [0, 1] for edge detection
        dmin, dmax = data.min(), data.max()
        if dmax > dmin:
            norm = (data - dmin) / (dmax - dmin)
        else:
            norm = np.zeros_like(data)

        edges = canny(norm, sigma=canny_sigma)

        records: RecordTable = RecordTable()

        if detect == "lines":
            tested_angles = np.linspace(-np.pi / 2, np.pi / 2, 180, endpoint=False)
            h, theta, d = hough_line(edges, theta=tested_angles)

            accum = field.replace(data=h.astype(np.float64), si_unit_z="", domain="frequency")

            peaks = hough_line_peaks(h, theta, d, num_peaks=n_features)
            for i, (hval, angle, dist) in enumerate(zip(*peaks)):
                angle_deg = np.degrees(angle)
                dist_phys = dist * field.dx
                records.append({"quantity": f"Line {i + 1} angle", "value": f"{angle_deg:.1f}", "unit": "deg"})
                records.append({"quantity": f"Line {i + 1} distance", "value": f"{dist_phys:.4g}", "unit": field.si_unit_xy})
                records.append({"quantity": f"Line {i + 1} votes", "value": f"{hval:.0f}", "unit": ""})

        elif detect == "circles":
            max_radius_px = max(min_radius_px + 1, max_radius_px)
            radii = np.arange(min_radius_px, max_radius_px + 1)
            h = hough_circle(edges, radii)

            # Sum over radii for the accumulator visualisation
            accum_data = h.sum(axis=0).astype(np.float64)
            accum = field.replace(data=accum_data, si_unit_z="")

            accum_list, cx_list, cy_list, rad_list = hough_circle_peaks(
                h, radii, total_num_peaks=n_features,
            )
            for i, (hval, cx, cy, r) in enumerate(zip(accum_list, cx_list, cy_list, rad_list)):
                cx_phys = cx * field.dx
                cy_phys = cy * field.dy
                r_phys = r * field.dx
                records.append({"quantity": f"Circle {i + 1} x", "value": f"{cx_phys:.4g}", "unit": field.si_unit_xy})
                records.append({"quantity": f"Circle {i + 1} y", "value": f"{cy_phys:.4g}", "unit": field.si_unit_xy})
                records.append({"quantity": f"Circle {i + 1} radius", "value": f"{r_phys:.4g}", "unit": field.si_unit_xy})

        else:
            raise ValueError(f"Unknown detect mode: {detect!r}")

        return (accum, records)
