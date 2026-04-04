"""Terrace fitting — segment atomic step terraces and extract step heights."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import label, uniform_filter

from backend.node_registry import register_node
from backend.data_types import DataField, RecordTable


@register_node(display_name="Terrace Fit")
class TerraceFit:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "n_terraces": ("INT", {"default": 0, "min": 0, "max": 50}),
                "broadening": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 20.0, "step": 0.1}),
                "poly_degree": ("INT", {"default": 0, "min": 0, "max": 3}),
                "output": (["residual", "fitted", "labels"], {"default": "residual"}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'result'),
        ('RECORD_TABLE', 'step_heights'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Segment a surface into flat terraces separated by atomic steps, fit "
        "a polynomial to each terrace, and extract step heights. "
        "Set n_terraces=0 for automatic detection via histogram clustering. "
    )

    def process(self, field: DataField, n_terraces: int, broadening: float,
                poly_degree: int, output: str) -> tuple:
        data = np.asarray(field.data, dtype=np.float64)

        # Smooth data to reduce noise before terrace detection
        smoothed = uniform_filter(data, size=max(3, int(broadening * 3)))

        if n_terraces <= 0:
            # Automatic detection: find peaks in height histogram
            n_terraces = self._auto_detect_terraces(smoothed)

        # Assign each pixel to the nearest terrace level using k-means-like clustering
        levels = self._cluster_terraces(smoothed, n_terraces)
        labels = np.zeros_like(data, dtype=np.int32)
        fitted = np.zeros_like(data)

        terrace_means = []

        # Direct assignment via argmin
        level_arr = np.array(levels)
        diffs = np.abs(smoothed[..., np.newaxis] - level_arr[np.newaxis, np.newaxis, :])
        labels = np.argmin(diffs, axis=-1).astype(np.int32)

        # Fit polynomial per terrace and build fitted surface
        yy, xx = np.mgrid[:data.shape[0], :data.shape[1]]
        x_phys = xx * field.dx
        y_phys = yy * field.dy

        for i in range(len(levels)):
            terrace_mask = labels == i
            if terrace_mask.sum() < max(3, (poly_degree + 1) ** 2):
                fitted[terrace_mask] = data[terrace_mask].mean() if terrace_mask.any() else 0
                terrace_means.append(float(data[terrace_mask].mean()) if terrace_mask.any() else 0.0)
                continue

            if poly_degree == 0:
                val = data[terrace_mask].mean()
                fitted[terrace_mask] = val
                terrace_means.append(float(val))
            else:
                # Build Vandermonde matrix for polynomial fit
                xp = x_phys[terrace_mask]
                yp = y_phys[terrace_mask]
                zp = data[terrace_mask]
                cols = []
                for py in range(poly_degree + 1):
                    for px in range(poly_degree + 1 - py):
                        cols.append(xp**px * yp**py)
                A = np.column_stack(cols)
                coeffs, _, _, _ = np.linalg.lstsq(A, zp, rcond=None)

                # Evaluate on all terrace pixels
                all_xp = x_phys[terrace_mask]
                all_yp = y_phys[terrace_mask]
                val = np.zeros(terrace_mask.sum())
                idx = 0
                for py in range(poly_degree + 1):
                    for px in range(poly_degree + 1 - py):
                        val += coeffs[idx] * all_xp**px * all_yp**py
                        idx += 1
                fitted[terrace_mask] = val
                terrace_means.append(float(val.mean()))

        # Sort terrace means and compute step heights
        terrace_means.sort()
        records = RecordTable()
        unit = field.si_unit_z
        for i, mean in enumerate(terrace_means):
            records.append({"quantity": f"Terrace {i + 1} height", "value": f"{mean:.4g}", "unit": unit})
        for i in range(1, len(terrace_means)):
            step = terrace_means[i] - terrace_means[i - 1]
            records.append({"quantity": f"Step {i}→{i + 1}", "value": f"{step:.4g}", "unit": unit})

        if output == "residual":
            out_data = data - fitted
        elif output == "fitted":
            out_data = fitted
        else:  # labels
            out_data = labels.astype(np.float64)

        return (field.replace(data=out_data), records)

    @staticmethod
    def _auto_detect_terraces(data: np.ndarray) -> int:
        """Detect number of terraces from histogram peaks."""
        hist, edges = np.histogram(data.ravel(), bins=256)
        smoothed = np.convolve(hist, np.ones(5) / 5, mode='same')
        # Find peaks: local maxima above mean
        threshold = smoothed.mean()
        peaks = []
        for i in range(1, len(smoothed) - 1):
            if smoothed[i] > smoothed[i - 1] and smoothed[i] > smoothed[i + 1] and smoothed[i] > threshold:
                peaks.append(i)
        return max(2, min(len(peaks), 20))

    @staticmethod
    def _cluster_terraces(data: np.ndarray, k: int) -> list[float]:
        """Simple 1D k-means clustering on height values."""
        flat = data.ravel()
        # Initialize with evenly spaced percentiles
        centers = [float(np.percentile(flat, 100 * (i + 0.5) / k)) for i in range(k)]

        for _ in range(50):
            # Assign
            center_arr = np.array(centers)
            dists = np.abs(flat[:, np.newaxis] - center_arr[np.newaxis, :])
            assignments = np.argmin(dists, axis=1)
            # Update
            new_centers = []
            for i in range(k):
                members = flat[assignments == i]
                new_centers.append(float(members.mean()) if len(members) > 0 else centers[i])
            if np.allclose(centers, new_centers, atol=1e-12):
                break
            centers = new_centers

        return sorted(centers)
