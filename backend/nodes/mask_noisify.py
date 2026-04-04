"""Mask noisify -- add random perturbation to mask boundaries."""

from __future__ import annotations
import numpy as np
from backend.node_registry import register_node
from backend.data_types import DataField
from backend.nodes.helpers import mask_to_bool, bool_to_mask, emit_mask_preview


@register_node(display_name="Mask Noisify")
class MaskNoisify:
    """
    Add random perturbation to mask boundaries.
    """
    _CUSTOM_PREVIEW = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("IMAGE",),
                "density": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01}),
                "direction": (["both", "add", "remove"],),
                "boundaries_only": ("BOOLEAN", {"default": True}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 999999}),
            },
            "optional": {
                "field": ("DATA_FIELD",),
            }
        }

    OUTPUTS = (
        ('IMAGE', 'mask'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Add random noise to a binary mask by flipping pixels near boundaries. "
        "Control the fraction of affected pixels with density, restrict changes "
        "to boundary pixels, and choose whether to add, remove, or both. "
        "Use a fixed seed for reproducible results."
    )

    KEYWORDS = ("random", "perturb", "boundary", "roughen", "jitter")

    def process(self, mask: np.ndarray, density: float, direction: str,
                boundaries_only: bool, seed: int,
                field: DataField | None = None) -> tuple:
        binary = mask_to_bool(mask)

        # Identify boundary pixels: pixels that differ from at least one neighbour
        if boundaries_only:
            boundary = np.zeros_like(binary)
            for shift_axis, shift_dir in [(0, 1), (0, -1), (1, 1), (1, -1)]:
                shifted = np.roll(binary, shift_dir, axis=shift_axis)
                boundary |= (binary != shifted)
        else:
            boundary = np.ones_like(binary)

        # Select candidate pixels based on direction
        if direction == "add":
            candidates = boundary & ~binary
        elif direction == "remove":
            candidates = boundary & binary
        else:  # "both"
            candidates = boundary

        # Randomly flip density fraction of candidates
        candidate_indices = np.argwhere(candidates)
        n_candidates = len(candidate_indices)

        if n_candidates > 0 and density > 0:
            rng = np.random.default_rng(seed)
            n_flip = int(round(density * n_candidates))
            n_flip = max(0, min(n_flip, n_candidates))
            if n_flip > 0:
                chosen = rng.choice(n_candidates, size=n_flip, replace=False)
                for idx in chosen:
                    r, c = candidate_indices[idx]
                    binary[r, c] = ~binary[r, c]

        out = bool_to_mask(binary)

        emit_mask_preview(field, out)

        return (out,)
