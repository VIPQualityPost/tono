from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField


@register_node(display_name="Inverse 2D FFT")
class FFT2DInverse:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "spectrum": ("DATA_FIELD",),
                "representation": (["magnitude", "log_magnitude", "psdf"],),
            },
            "optional": {
                "phase": ("DATA_FIELD",),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'image'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Reconstruct a spatial-domain image from a 2D frequency spectrum. "
        "For exact reconstruction, connect magnitude/phase (or log magnitude/phase, "
        "or PSDF/phase) from the 2D FFT node. If phase is omitted, zero phase is assumed."
    )

    def process(self, spectrum: DataField, representation: str, phase: DataField | None = None) -> tuple:
        if spectrum.domain != "frequency":
            raise ValueError("Inverse 2D FFT requires a frequency-domain DATA_FIELD input.")

        if phase is not None:
            if phase.data.shape != spectrum.data.shape:
                raise ValueError("Phase input must have the same shape as the spectrum.")
            if phase.domain != "frequency":
                raise ValueError("Phase input must also be a frequency-domain DATA_FIELD.")

        amplitude = self._resolve_amplitude(spectrum, representation)
        phase_data = phase.data if phase is not None else np.zeros_like(amplitude)
        F = amplitude * np.exp(1j * phase_data)

        spatial = np.fft.ifft2(np.fft.ifftshift(F)).real
        xreal, yreal = self._recover_spatial_extent(spectrum, representation)
        z_unit = self._recover_z_unit(spectrum, representation, phase)

        out_field = DataField(
            data=spatial,
            xreal=xreal,
            yreal=yreal,
            si_unit_xy="m",
            si_unit_z=z_unit,
            domain="spatial",
            colormap=spectrum.colormap,
        )
        return (out_field,)

    def _resolve_amplitude(self, spectrum: DataField, representation: str) -> np.ndarray:
        data = np.asarray(spectrum.data, dtype=np.float64)

        if representation == "magnitude":
            return np.clip(data, 0.0, None)
        if representation == "log_magnitude":
            return np.expm1(data)
        if representation == "psdf":
            xreal, yreal = self._recover_spatial_extent(spectrum, representation)
            n = spectrum.xres * spectrum.yres
            dx = xreal / spectrum.xres
            dy = yreal / spectrum.yres
            scale = n * 4.0 * np.pi ** 2 / (dx * dy)
            return np.sqrt(np.clip(data, 0.0, None) * scale)

        raise ValueError(f"Unsupported spectrum representation: {representation}")

    def _recover_spatial_extent(self, spectrum: DataField, representation: str) -> tuple[float, float]:
        if representation == "psdf":
            xreal = 2.0 * np.pi * spectrum.xres / spectrum.xreal
            yreal = 2.0 * np.pi * spectrum.yres / spectrum.yreal
        else:
            xreal = spectrum.xres / spectrum.xreal
            yreal = spectrum.yres / spectrum.yreal
        return float(xreal), float(yreal)

    def _recover_z_unit(
        self,
        spectrum: DataField,
        representation: str,
        phase: DataField | None,
    ) -> str:
        if phase is not None and isinstance(phase.si_unit_z, str) and phase.si_unit_z.strip():
            return phase.si_unit_z

        if representation != "psdf":
            return spectrum.si_unit_z

        unit = str(spectrum.si_unit_z or "").strip()
        if unit.startswith("(") and ")^2 m^2" in unit:
            return unit.split(")^2 m^2", 1)[0][1:]
        if unit.endswith("^2 m^2"):
            return unit[:-6].removesuffix("^2").strip()
        return ""
