"""Tip shape estimation — estimate SPM tip geometry from known calibration features."""

from __future__ import annotations

import numpy as np

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable


@register_node(display_name="Tip Shape Estimate")
class TipShapeEstimate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "feature_type": (["edge", "sphere", "cylinder"], {"default": "edge"}),
                "feature_radius": ("FLOAT", {
                    "default": 100e-9, "min": 1e-9, "max": 100e-6, "step": 1e-9,
                }),
                "n_points": ("INT", {"default": 100, "min": 10, "max": 1000}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'tip_shape'),
        ('RECORD_TABLE', 'parameters'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Estimate SPM tip geometry from a known calibration feature. "
        "Supported features: edge (sharp step), sphere (calibration ball), "
        "cylinder (calibration wire). The image of a known feature is a "
        "dilation of the feature with the tip; by subtracting the known "
        "feature contribution the tip shape can be recovered. "
        "The 2D tip is built by revolving the 1D radial profile (axial "
        "symmetry assumption). Output parameters include estimated tip "
        "radius of curvature at the apex and half-cone angle. "
    )

    KEYWORDS = ("calibration", "villarrubia", "tipshape", "radius", "apex", "half angle", "edge", "sphere", "cylinder", "dilation")

    def process(
        self,
        field: DataField,
        feature_type: str,
        feature_radius: float,
        n_points: int,
    ) -> tuple:
        data = field.data.astype(np.float64)
        ny, nx = data.shape
        pixel_size = (field.dx + field.dy) * 0.5

        # ── Step 1: Extract 1D tip profile depending on feature type ──────

        if feature_type == "edge":
            tip_profile_1d = self._estimate_from_edge(data, pixel_size, n_points)

        elif feature_type == "sphere":
            tip_profile_1d = self._estimate_from_sphere(
                data, pixel_size, feature_radius, n_points,
            )

        elif feature_type == "cylinder":
            tip_profile_1d = self._estimate_from_cylinder(
                data, pixel_size, feature_radius, n_points,
            )

        else:
            raise ValueError(
                f"Unknown feature_type {feature_type!r}. "
                "Choose: edge, sphere, cylinder."
            )

        # ── Step 2: Build 2D tip by revolution (axial symmetry) ───────────

        n_tip = n_points if n_points % 2 == 1 else n_points + 1
        ci = n_tip // 2
        offsets = np.arange(n_tip) - ci
        gx, gy = np.meshgrid(offsets, offsets)
        r_grid = np.sqrt(gx ** 2 + gy ** 2)

        # The 1D profile goes from r = 0 to r = max_r.
        # Interpolate for every pixel in the 2D grid.
        r_1d = np.linspace(0, ci, len(tip_profile_1d))
        tip_2d = np.interp(r_grid, r_1d, tip_profile_1d, right=0.0)

        # Convention: apex (center) is the maximum; minimum is 0.
        tip_2d -= tip_2d.min()

        xreal = n_tip * pixel_size
        tip_field = DataField(
            data=tip_2d,
            xreal=xreal,
            yreal=xreal,
            si_unit_xy=field.si_unit_xy,
            si_unit_z=field.si_unit_z,
        )

        # ── Step 3: Estimate tip parameters ───────────────────────────────

        tip_radius, half_angle = self._estimate_parameters(
            tip_profile_1d, pixel_size,
        )

        table = RecordTable([
            {"quantity": "tip_radius", "value": tip_radius, "unit": field.si_unit_z},
            {"quantity": "half_angle", "value": half_angle, "unit": "deg"},
        ])

        return (tip_field, table)

    # ── Feature-specific estimation methods ───────────────────────────────

    @staticmethod
    def _estimate_from_edge(
        data: np.ndarray,
        pixel_size: float,
        n_points: int,
    ) -> np.ndarray:
        """
        Edge feature: the tip shape is the mirror of the steepest edge
        cross-section in the image.

        Find the row with the maximum gradient magnitude, extract the
        cross-section at that location, mirror and normalise.

        Returns a radial profile: index 0 = apex (maximum), decreasing
        outward.
        """
        ny, nx = data.shape

        # Compute row-wise gradient magnitude to find the steepest edge.
        grad = np.abs(np.diff(data, axis=1))
        row_grad = grad.sum(axis=1)
        best_row = int(np.argmax(row_grad))

        profile = data[best_row, :]

        # Mirror: the tip is the complement of the edge profile.
        tip_raw = np.max(profile) - profile[::-1]

        # Find the peak of the mirrored profile and take the radial
        # (half) profile from apex outward.
        peak = int(np.argmax(tip_raw))
        # Use the longer side from the peak to preserve resolution.
        left = tip_raw[:peak + 1][::-1]   # apex to left edge, reversed
        right = tip_raw[peak:]             # apex to right edge
        half = left if len(left) >= len(right) else right
        half = half.copy()
        # Ensure monotonically decreasing from apex.
        for i in range(1, len(half)):
            if half[i] > half[i - 1]:
                half[i] = half[i - 1]

        # Resample to n_points.
        x_raw = np.linspace(0, 1, len(half))
        x_out = np.linspace(0, 1, n_points)
        tip_profile = np.interp(x_out, x_raw, half)

        return tip_profile

    @staticmethod
    def _estimate_from_sphere(
        data: np.ndarray,
        pixel_size: float,
        radius: float,
        n_points: int,
    ) -> np.ndarray:
        """
        Sphere feature: dilation model z_measured = z_sphere (+) z_tip.

        Extract radial profile from the highest point and subtract the
        ideal sphere contribution to recover the tip profile.

        Returns a radial profile: index 0 = apex (maximum), decreasing
        outward.
        """
        ny, nx = data.shape

        # Find the highest point (apex of the imaged sphere).
        peak_idx = np.unravel_index(np.argmax(data), data.shape)
        cy, cx = peak_idx

        # Extract radial profile by averaging azimuthally.
        max_r = min(cy, ny - 1 - cy, cx, nx - 1 - cx)
        if max_r < 2:
            max_r = min(ny, nx) // 2

        Y, X = np.ogrid[:ny, :nx]
        r_map = np.sqrt(((X - cx) * pixel_size) ** 2 + ((Y - cy) * pixel_size) ** 2)

        n_bins = min(max_r, n_points)
        r_edges = np.linspace(0, max_r * pixel_size, n_bins + 1)
        radial_profile = np.zeros(n_bins)
        for i in range(n_bins):
            mask = (r_map >= r_edges[i]) & (r_map < r_edges[i + 1])
            if mask.any():
                radial_profile[i] = data[mask].mean()
            elif i > 0:
                radial_profile[i] = radial_profile[i - 1]

        r_centers = 0.5 * (r_edges[:-1] + r_edges[1:])

        # Ideal sphere profile: z_sphere(r) = sqrt(R^2 - r^2) for r < R, else 0.
        sphere_profile = np.where(
            r_centers < radius,
            np.sqrt(np.maximum(radius ** 2 - r_centers ** 2, 0.0)),
            0.0,
        )

        # Tip profile = measured - sphere (dilation subtraction).
        tip_raw = radial_profile - sphere_profile
        # Shift so that the apex (index 0) is the maximum.
        tip_raw = tip_raw - tip_raw.min()
        # Ensure monotonically decreasing from apex outward by clamping.
        for i in range(1, len(tip_raw)):
            if tip_raw[i] > tip_raw[i - 1]:
                tip_raw[i] = tip_raw[i - 1]

        # Resample to n_points.
        x_raw = np.linspace(0, 1, len(tip_raw))
        x_out = np.linspace(0, 1, n_points)
        tip_profile = np.interp(x_out, x_raw, tip_raw)

        return tip_profile

    @staticmethod
    def _estimate_from_cylinder(
        data: np.ndarray,
        pixel_size: float,
        radius: float,
        n_points: int,
    ) -> np.ndarray:
        """
        Cylinder feature: extract cross-section perpendicular to the
        cylinder axis and subtract ideal cylinder profile.

        The cylinder axis is assumed to run along the direction with the
        least height variation.

        Returns a radial profile: index 0 = apex (maximum), decreasing
        outward.
        """
        ny, nx = data.shape

        # Determine cylinder axis: compare row-wise vs column-wise variance.
        row_var = np.var(np.diff(data, axis=1))
        col_var = np.var(np.diff(data, axis=0))

        if row_var > col_var:
            # Cylinder axis along columns -> cross-section along rows.
            profile = data.mean(axis=0)
        else:
            # Cylinder axis along rows -> cross-section along columns.
            profile = data.mean(axis=1)

        n_prof = len(profile)
        peak = int(np.argmax(profile))

        # Ideal cylinder cross-section: z = sqrt(R^2 - x^2) for |x| < R.
        x_phys = (np.arange(n_prof) - peak) * pixel_size
        cyl_profile = np.where(
            np.abs(x_phys) < radius,
            np.sqrt(np.maximum(radius ** 2 - x_phys ** 2, 0.0)),
            0.0,
        )

        # Tip = measured - cylinder.
        tip_raw = profile - cyl_profile
        tip_raw -= tip_raw.min()

        # Take the radial (half) profile from the peak outward.
        left = tip_raw[:peak + 1][::-1]
        right = tip_raw[peak:]
        half = left if len(left) >= len(right) else right
        # Ensure monotonically decreasing from apex.
        for i in range(1, len(half)):
            if half[i] > half[i - 1]:
                half[i] = half[i - 1]

        # Resample to n_points.
        x_raw = np.linspace(0, 1, len(half))
        x_out = np.linspace(0, 1, n_points)
        tip_profile = np.interp(x_out, x_raw, half)

        return tip_profile

    # ── Parameter estimation ──────────────────────────────────────────────

    @staticmethod
    def _estimate_parameters(
        tip_profile: np.ndarray,
        pixel_size: float,
    ) -> tuple[float, float]:
        """
        Estimate tip radius of curvature at the apex and half-cone angle
        from the 1D radial profile.

        tip_radius: fitted from the parabolic approximation near the apex,
            z(r) ~ z_max - r^2 / (2R)  =>  R = r^2 / (2 * (z_max - z(r)))

        half_angle: from the slope of the tip walls in the outer half,
            tan(half_angle) = dz/dr  =>  half_angle = arctan(slope)
        """
        n = len(tip_profile)
        r = np.linspace(0, (n - 1) * pixel_size, n)

        # ── Tip radius from apex curvature ────────────────────────────────
        # Use a few points near the apex for a parabolic fit: z = a - b*r^2
        n_apex = max(3, n // 10)
        r_apex = r[:n_apex]
        z_apex = tip_profile[:n_apex]

        if len(r_apex) >= 2 and r_apex[-1] > 0:
            # Fit z = c0 + c1 * r^2
            A = np.vstack([np.ones(n_apex), r_apex ** 2]).T
            try:
                coeffs = np.linalg.lstsq(A, z_apex, rcond=None)[0]
                c1 = coeffs[1]
                # z = z_max - r^2/(2R) => c1 = -1/(2R) => R = -1/(2*c1)
                if c1 < 0:
                    tip_radius = -1.0 / (2.0 * c1)
                else:
                    tip_radius = float('inf')
            except np.linalg.LinAlgError:
                tip_radius = float('inf')
        else:
            tip_radius = float('inf')

        # ── Half-angle from outer wall slope ──────────────────────────────
        # Use the outer 50% of the profile.
        mid = n // 2
        if mid < n - 1:
            r_outer = r[mid:]
            z_outer = tip_profile[mid:]
            if len(r_outer) >= 2:
                dr = r_outer[-1] - r_outer[0]
                dz = z_outer[-1] - z_outer[0]
                if dr > 0:
                    slope = abs(dz / dr)
                    half_angle = np.degrees(np.arctan(slope))
                else:
                    half_angle = 0.0
            else:
                half_angle = 0.0
        else:
            half_angle = 0.0

        return tip_radius, half_angle
