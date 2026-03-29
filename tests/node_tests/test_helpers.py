import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


def test_list_channels():
    from backend.nodes.helpers import list_channels, list_folder_paths
    from backend.nodes.folder import Folder

    ch = list_channels("/nonexistent/file.ibw")
    assert len(ch) == 1
    assert ch[0]["name"] == "field"

    ibw_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "demo", "BR_New20012.ibw"))
    if os.path.exists(ibw_path):
        ch = list_channels(ibw_path)
        assert len(ch) == 4
        names = [c["name"] for c in ch]
        assert "HeightRetrace" in names
        assert "AmplitudeRetrace" in names
        assert all(c["type"] == "DATA_FIELD" for c in ch)

    with tempfile.TemporaryDirectory() as tmpdir:
        img = Image.fromarray(np.zeros((8, 8), dtype=np.uint8))
        path = os.path.join(tmpdir, "test.png")
        img.save(path)

        ch = list_channels(path)
        assert len(ch) == 1
        assert ch[0]["name"] == "field"

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.npy")
        np.save(path, np.zeros((4, 4)))
        ch = list_channels(path)
        assert len(ch) == 1

    with tempfile.TemporaryDirectory() as tmpdir:
        img = Image.fromarray(np.zeros((8, 8), dtype=np.uint8))
        png_path = os.path.join(tmpdir, "a.png")
        npy_path = os.path.join(tmpdir, "b.npy")
        gwy_path = os.path.join(tmpdir, "c.gwy")
        sxm_path = os.path.join(tmpdir, "d.sxm")
        ibw_path2 = os.path.join(tmpdir, "e.ibw")
        txt_path = os.path.join(tmpdir, "notes.txt")
        img.save(png_path)
        np.save(npy_path, np.zeros((4, 4)))
        Path(gwy_path).write_bytes(b"gwy")
        Path(sxm_path).write_bytes(b"sxm")
        Path(ibw_path2).write_bytes(b"ibw")
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write("ignore me")

        paths = list_folder_paths(tmpdir)
        assert [entry["name"] for entry in paths] == ["directory", "a.png", "b.npy", "c.gwy", "d.sxm", "e.ibw"]
        assert Path(paths[0]["path"]).resolve() == Path(tmpdir).resolve()
        assert paths[0]["type"] == "DIRECTORY"
        assert all(entry["type"] == "FILE_PATH" for entry in paths[1:])

        folder_node = Folder()
        folder_result = folder_node.list_files(tmpdir)
        assert folder_result == tuple(entry["path"] for entry in paths)
