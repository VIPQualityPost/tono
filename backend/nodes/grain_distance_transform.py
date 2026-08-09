from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt

from backend.data_types import DataField
from backend.node_registry import register_node
from backend.nodes.helpers import mask_to_bool


def _normalize_mask(mask: np.ndarray) -> np.ndarray:
    data = np.asarray(mask)
    if data.ndim != 2:
        raise ValueError("Grain Distance Transform requires a 2-D mask.")
    return mask_to_bool(data)


def _prepare_mask(binary: np.ndarray, from_border: bool) -> tuple[np.ndarray, tuple[slice, slice]]:
    binary = np.asarray(binary, dtype=bool)
    if from_border:
        return binary, (slice(None), slice(None))

    pad = max(binary.shape)
    padded = np.pad(binary, pad, mode="constant", constant_values=True)
    padded[0, :] = False
    padded[-1, :] = False
    padded[:, 0] = False
    padded[:, -1] = False
    return padded, (slice(pad, pad + binary.shape[0]), slice(pad, pad + binary.shape[1]))


@lru_cache(maxsize=32)
def _distance_structures() -> tuple[np.ndarray, np.ndarray]:
    cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
    square = np.ones((3, 3), dtype=bool)
    cross.setflags(write=False)
    square.setflags(write=False)
    return cross, square


def _simple_distance_transform(binary: np.ndarray, distance_type: str, from_border: bool) -> np.ndarray:
    work, crop = _prepare_mask(binary, from_border)
    result = np.zeros(work.shape, dtype=np.float64)
    current = work.copy()
    cross, square = _distance_structures()

    if distance_type == "cityblock":
        sequence = (cross,)
    elif distance_type == "chess":
        sequence = (square,)
    elif distance_type == "octagonal48":
        sequence = (cross, square)
    elif distance_type == "octagonal84":
        sequence = (square, cross)
    else:
        raise ValueError(f"Unsupported simple distance type: {distance_type}")

    step = 1.0
    iteration = 0
    while np.any(current):
        structure = sequence[iteration % len(sequence)]
        eroded = binary_erosion(current, structure=structure, border_value=0)
        removed = current & ~eroded
        result[removed] = step
        current = eroded
        step += 1.0
        iteration += 1

    return result[crop]


def _euclidean_distance_transform(binary: np.ndarray, from_border: bool) -> np.ndarray:
    if from_border:
        work = np.pad(np.asarray(binary, dtype=bool), 1, mode="constant", constant_values=False)
        return np.asarray(distance_transform_edt(work), dtype=np.float64)[1:-1, 1:-1]

    work, crop = _prepare_mask(binary, False)
    return np.asarray(distance_transform_edt(work), dtype=np.float64)[crop]


def _distance_transform(binary: np.ndarray, distance_type: str, from_border: bool) -> np.ndarray:
    if distance_type == "euclidean":
        return _euclidean_distance_transform(binary, from_border)
    if distance_type == "octagonal":
        d48 = _simple_distance_transform(binary, "octagonal48", from_border)
        d84 = _simple_distance_transform(binary, "octagonal84", from_border)
        return 0.5 * (d48 + d84)
    return _simple_distance_transform(binary, distance_type, from_border)


@register_node(display_name="Grain Distance Transform")
class GrainDistanceTransform:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "field": ("DATA_FIELD",),
                "mask": ("IMAGE",),
                "distance_type": (["euclidean", "cityblock", "chess", "octagonal48", "octagonal84", "octagonal"], {"default": "euclidean"}),
                "output_type": (["interior", "exterior", "signed"], {"default": "interior"}),
                "from_border": ("BOOLEAN", {"default": True}),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'distance'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Compute the mask distance transform using interior, exterior, or signed output. "
        "Supports Euclidean, city-block, chessboard, and octagonal distance variants, with optional "
        "image-boundary handling matching mask_edt."
    )

    KEYWORDS = ("edt", "euclidean", "chessboard", "cityblock", "manhattan")

    def process(
        self,
        field: DataField,
        mask: np.ndarray,
        distance_type: str,
        output_type: str,
        from_border: bool,
    ) -> tuple:
        binary = _normalize_mask(mask)

        interior = _distance_transform(binary, distance_type, bool(from_border))
        interior *= binary

        if output_type == "interior":
            distance = interior
        else:
            exterior_binary = ~binary
            exterior = _distance_transform(exterior_binary, distance_type, bool(from_border))
            exterior *= exterior_binary
            if output_type == "exterior":
                distance = exterior
            elif output_type == "signed":
                distance = interior - exterior
            else:
                raise ValueError(f"Unsupported output type: {output_type}")

        scale = float(np.sqrt(field.dx * field.dy))
        result = field.replace(
            data=np.asarray(distance, dtype=np.float64) * scale,
            si_unit_z=field.si_unit_xy,
        )
        return (result,)
