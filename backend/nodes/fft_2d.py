from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="2D FFT")
class FFT2D:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "windowing": (["hann", "hamming", "blackman", "none"],),
                "level": (["mean", "plane", "none"],),
            }
        }

    RETURN_TYPES = ("DATA_FIELD", "DATA_FIELD", "DATA_FIELD", "DATA_FIELD")
    RETURN_NAMES = ("log_magnitude", "magnitude", "phase", "psdf")
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the 2D FFT with optional windowing and mean/plane subtraction. "
        "Outputs log magnitude, magnitude, phase, and PSDF as separate channels. "
        "Equivalent to gwy_data_field_2dfft / gwy_data_field_2dpsdf."
    )

    def process(self, field: DataField, windowing: str, level: str) -> tuple:
        data = field.data.copy()
        yres, xres = data.shape

        if level == "mean":
            data -= data.mean()
        elif level == "plane":
            yy, xx = np.mgrid[0:yres, 0:xres]
            xx_f = xx.ravel().astype(np.float64)
            yy_f = yy.ravel().astype(np.float64)
            zz_f = data.ravel()
            A = np.column_stack([np.ones_like(xx_f), xx_f, yy_f])
            coeffs, _, _, _ = np.linalg.lstsq(A, zz_f, rcond=None)
            plane = (coeffs[0] + coeffs[1] * xx + coeffs[2] * yy)
            data -= plane

        if windowing != "none":
            t_y = (np.arange(yres) + 0.5) / yres
            t_x = (np.arange(xres) + 0.5) / xres
            if windowing == "hann":
                wy = 0.5 - 0.5 * np.cos(2 * np.pi * t_y)
                wx = 0.5 - 0.5 * np.cos(2 * np.pi * t_x)
            elif windowing == "hamming":
                wy = 0.54 - 0.46 * np.cos(2 * np.pi * t_y)
                wx = 0.54 - 0.46 * np.cos(2 * np.pi * t_x)
            elif windowing == "blackman":
                wy = 0.42 - 0.5 * np.cos(2 * np.pi * t_y) + 0.08 * np.cos(4 * np.pi * t_y)
                wx = 0.42 - 0.5 * np.cos(2 * np.pi * t_x) + 0.08 * np.cos(4 * np.pi * t_x)
            else:
                wy = np.ones(yres)
                wx = np.ones(xres)
            data *= np.outer(wy, wx)

        F = np.fft.fftshift(np.fft.fft2(data))
        n = xres * yres

        magnitude = np.abs(F)
        log_magnitude = np.log1p(magnitude)
        phase = np.angle(F)

        dx = field.xreal / xres
        dy = field.yreal / yres
        psdf = (magnitude ** 2) * dx * dy / (n * 4.0 * np.pi ** 2)

        spatial_freq_xreal = xres / field.xreal
        spatial_freq_yreal = yres / field.yreal
        angular_freq_xreal = 2.0 * np.pi * xres / field.xreal
        angular_freq_yreal = 2.0 * np.pi * yres / field.yreal

        return (
            DataField(
                data=log_magnitude,
                xreal=spatial_freq_xreal,
                yreal=spatial_freq_yreal,
                si_unit_xy="1/m",
                si_unit_z=field.si_unit_z,
                domain="frequency",
                colormap=field.colormap,
            ),
            DataField(
                data=magnitude,
                xreal=spatial_freq_xreal,
                yreal=spatial_freq_yreal,
                si_unit_xy="1/m",
                si_unit_z=field.si_unit_z,
                domain="frequency",
                colormap=field.colormap,
            ),
            DataField(
                data=phase,
                xreal=spatial_freq_xreal,
                yreal=spatial_freq_yreal,
                si_unit_xy="1/m",
                si_unit_z=field.si_unit_z,
                domain="frequency",
                colormap=field.colormap,
            ),
            DataField(
                data=psdf,
                xreal=angular_freq_xreal,
                yreal=angular_freq_yreal,
                si_unit_xy="1/m",
                si_unit_z=f"({field.si_unit_z})^2 m^2",
                domain="frequency",
                colormap=field.colormap,
            ),
        )
