from __future__ import annotations
from backend.node_registry import register_node
from backend.data_types import COLORMAPS
from backend.nodes.helpers import DEMO_DIR, _list_demo_files


@register_node(display_name="Image (Demo)")
class ImageDemo:
    @classmethod
    def INPUT_TYPES(cls):
        choices = _list_demo_files() or ["(no demo files found)"]
        return {
            "required": {
                "name": (choices,),
                "colormap": (list(COLORMAPS), {"hide_when_input_connected": "colormap_map"}),
            },
            "optional": {
                "colormap_map": ("COLORMAP", {"label": "colormap"}),
            },
        }

    OUTPUTS = (
        ('DATA_FIELD', 'field'),
        ('DATA_FIELD', 'channel_2'),
        ('DATA_FIELD', 'channel_3'),
    )
    FUNCTION = "load"

    DESCRIPTION = "Load a bundled demo file so you can try the app without providing your own data."

    KEYWORDS = ("example", "sample", "test")

    def load(self, name: str = "", colormap: str = "viridis", colormap_map=None):
        from backend.nodes.image import Image
        loader = Image()
        demo_path = DEMO_DIR / name
        if not demo_path.exists():
            raise FileNotFoundError(f"Demo file not found: {name}")
        return loader.load(filename=str(demo_path), colormap=colormap, colormap_map=colormap_map)[1:][:3]
