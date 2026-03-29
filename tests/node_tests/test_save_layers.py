import os
import tempfile

import numpy as np
import tifffile
from PIL import Image

from tests.node_tests._shared import make_field


def test_save_image():
    from backend.nodes.save_layers import SaveImage

    node = SaveImage()
    input_types = SaveImage.INPUT_TYPES()
    field_spec = input_types["optional"]["field_0"]
    assert field_spec[0] == "DATA_FIELD"
    assert field_spec[1]["accepted_types"] == ["IMAGE", "ANNOTATION_SOURCE"]

    field_a = make_field(data=np.random.default_rng(4).random((32, 32)))
    field_b = make_field(data=np.random.default_rng(5).random((32, 32)))
    annotated = np.zeros((24, 24, 3), dtype=np.uint8)
    annotated[..., 0] = 255

    with tempfile.TemporaryDirectory() as tmpdir:
        tiff_path = os.path.join(tmpdir, "out.tiff")
        node.save(filename=tiff_path, format="TIFF", field_0=field_a)
        assert os.path.exists(tiff_path)
        im = Image.open(tiff_path)
        assert im.n_frames == 1
        assert np.array(im).shape == (32, 32)

        tiff_path2 = os.path.join(tmpdir, "multi.tiff")
        node.save(filename=tiff_path2, format="TIFF", field_0=field_a, field_1=field_b)
        im2 = Image.open(tiff_path2)
        assert im2.n_frames == 2

        annotated_tiff = os.path.join(tmpdir, "annotated.tiff")
        node.save(filename=annotated_tiff, format="TIFF", field_0=annotated, layer_name_0="annotated overview")
        with tifffile.TiffFile(annotated_tiff) as tif:
            assert len(tif.pages) == 1
            assert tif.pages[0].description == "annotated overview"
            assert tif.pages[0].asarray().shape == annotated.shape

        npz_path = os.path.join(tmpdir, "out.npz")
        node.save(filename=npz_path, format="NPZ", field_0=field_a, field_1=annotated, layer_name_0="height map", layer_name_1="annotated-overview")
        assert os.path.exists(npz_path)
        npz = np.load(npz_path)
        assert len(npz.files) == 2
        assert np.allclose(npz["height_map"], field_a.data)
        assert np.array_equal(npz["annotated_overview"], annotated)

        wrong_ext = os.path.join(tmpdir, "output.png")
        node.save(filename=wrong_ext, format="TIFF", field_0=field_a)
        assert os.path.exists(os.path.join(tmpdir, "output.tiff"))

        driven_dir = os.path.join(tmpdir, "nested-output")
        node.save(filename="driven_name", directory=driven_dir, format="NPZ", field_0=field_a)
        assert os.path.exists(os.path.join(driven_dir, "driven_name.npz"))

        try:
            node.save(filename="bad", directory=os.path.join(tmpdir, "looks_like_file.txt"), format="TIFF", field_0=field_a)
            assert False, "Should have raised ValueError for file-like directory path"
        except ValueError:
            pass

        try:
            node.save(filename=os.path.join(tmpdir, "empty.tiff"), format="TIFF")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

        try:
            node.save(filename="", format="TIFF", field_0=field_a)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
