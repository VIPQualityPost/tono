from __future__ import annotations

import numpy as np

from backend.data_types import DataField
from backend.node_registry import register_node


@register_node(display_name="Template Match")
class TemplateMatch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("DATA_FIELD",),
                "template": ("DATA_FIELD",),
                "threshold": (
                    "FLOAT",
                    {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.05},
                ),
            }
        }

    OUTPUTS = (
        ('DATA_FIELD', 'score'),
        ('IMAGE', 'detections'),
    )
    FUNCTION = "process"

    DESCRIPTION = (
        "Find a template pattern within a larger data field using normalised cross-correlation. "
        "The score output shows match quality (1 = perfect match). Detections mask marks positions "
        "above the threshold. Equivalent to Gwyddion maskcor.c."
    )

    def process(
        self,
        image: DataField,
        template: DataField,
        threshold: float,
    ) -> tuple:
        from skimage.feature import match_template

        score = match_template(image.data, template.data, pad_input=True)

        # Clip to [0, 1] for display (match_template returns values in [-1, 1])
        score_clipped = np.clip(score, 0.0, 1.0)

        detections = (score_clipped >= float(threshold)).astype(np.uint8) * 255

        score_field = image.replace(data=score_clipped)
        return (score_field, detections)
