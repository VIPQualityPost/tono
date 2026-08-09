"""Facet analysis — orientation distribution of surface facets."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable
from backend.execution_context import emit_table


@register_node(display_name="Facet Analysis")
class FacetAnalysis:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "n_bins": ("INT", {"default": 180, "min": 30, "max": 720}),
                "kernel_size": ("INT", {"default": 3, "min": 3, "max": 9, "step": 2}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'facet_map'),
        ('RECORD_TABLE', 'measurement'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the facet orientation distribution of a surface. "
        "Outputs a 2D histogram (stereographic projection) where the x-axis "
        "is the azimuthal angle (phi) and y-axis is the inclination (theta). "
        "Intensity represents how much surface area faces each orientation. "
        "The measurement table reports the mean azimuth/inclination and the "
        "dominant orientation of the steepest (top 10%) facets."
    )

    KEYWORDS = ("orientation", "stereographic", "azimuth", "inclination", "slope", "crystal")

    def process(self, field: DataField, n_bins: int, kernel_size: int) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        # Compute gradients with Sobel-like kernel for robustness
        from scipy.ndimage import sobel
        gx = sobel(data, axis=1) / (kernel_size * field.dx)
        gy = sobel(data, axis=0) / (kernel_size * field.dy)

        # Convert to spherical angles
        theta = np.arctan(np.sqrt(gx**2 + gy**2))  # inclination from vertical
        phi = np.arctan2(gy, gx)  # azimuthal angle

        # Map to [0, pi/2] and [0, 2*pi]
        theta_flat = theta.ravel()
        phi_flat = (phi.ravel() + 2 * np.pi) % (2 * np.pi)

        # Build 2D histogram (stereographic projection)
        theta_max = float(theta_flat.max()) if theta_flat.size > 0 else np.pi / 4
        theta_max = max(theta_max, 0.01)

        n_theta = max(1, n_bins // 4)
        n_phi = n_bins

        hist, _, _ = np.histogram2d(
            theta_flat,
            phi_flat,
            bins=[n_theta, n_phi],
            range=[[0.0, theta_max], [0.0, 2 * np.pi]],
        )

        # Normalise so it represents a probability density
        total = hist.sum()
        if total > 0:
            hist = hist / total

        facet_field = DataField(
            data=hist,
            xreal=360.0,
            yreal=np.degrees(theta_max),
            si_unit_xy="deg",
            si_unit_z="",
            domain="spatial",
        )

        rows = []
        if theta_flat.size > 0:
            mean_azimuth = float(np.degrees(
                np.arctan2(np.mean(np.sin(phi_flat)), np.mean(np.cos(phi_flat))))) % 360.0
            mean_inclination = float(np.degrees(np.mean(theta_flat)))
            steep = theta_flat >= np.percentile(theta_flat, 90)
            dom_phi = phi_flat[steep]
            dom_theta = theta_flat[steep]
            dominant_azimuth = float(np.degrees(
                np.arctan2(np.mean(np.sin(dom_phi)), np.mean(np.cos(dom_phi))))) % 360.0
            dominant_inclination = float(np.degrees(np.mean(dom_theta)))
            rows = [
                {"quantity": "Mean azimuth", "value": mean_azimuth, "unit": "deg"},
                {"quantity": "Mean inclination", "value": mean_inclination, "unit": "deg"},
                {"quantity": "Dominant azimuth", "value": dominant_azimuth, "unit": "deg"},
                {"quantity": "Dominant inclination", "value": dominant_inclination, "unit": "deg"},
            ]
        measurement = RecordTable(rows)
        emit_table(measurement)
        return (facet_field, measurement)
