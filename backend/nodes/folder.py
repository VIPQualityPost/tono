from __future__ import annotations
from backend.node_registry import register_node
from backend.nodes.helpers import list_folder_paths


@register_node(display_name="Folder")
class Folder:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder": ("FOLDER_PICKER", {"default": "", "placement": "top"}),
            }
        }

    OUTPUTS = (
        ('DIRECTORY', 'directory'),
    )
    FUNCTION = "list_files"

    DESCRIPTION = (
        "Pick a folder and output its directory path plus one file socket per compatible image, array, or SPM file inside it. "
    )

    KEYWORDS = ("directory", "batch", "load", "open")

    def list_files(self, folder: str) -> tuple:
        entries = list_folder_paths(folder)
        if not entries:
            return tuple()
        return tuple(item["path"] for item in entries)
