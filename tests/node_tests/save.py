import json
import os
import tempfile
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image as PILImage

from backend.data_types import DataField, ImageData, LineData, RecordTable, MeshModel, DataTable


def test_save_generic():
    from backend.nodes.save import Save

    node = Save()
    value_spec = node.INPUT_TYPES()["required"]["value"]
    assert value_spec[0] == "DATA_FIELD"
    assert value_spec[1]["accepted_types"] == [
        "IMAGE", "ANNOTATION_SOURCE", "LINE", "RECORD_TABLE", "DATA_TABLE", "MESH_MODEL", "FLOAT",
    ]
    format_choices = node.INPUT_TYPES()["required"]["format"][1]["choices_by_source_type"]
    assert format_choices["ANNOTATION_SOURCE"] == format_choices["IMAGE"]

    with tempfile.TemporaryDirectory() as tmpdir:
        node.save(filename="scalar", directory_path=tmpdir, format="TXT", value=3.5)
        assert Path(tmpdir, "scalar.txt").read_text(encoding="utf-8").strip() == "3.5"
        node.save(filename="scalar_json", directory_path=tmpdir, format="JSON", value=3.5)
        assert json.loads(Path(tmpdir, "scalar_json.json").read_text(encoding="utf-8")) == {"value": 3.5}

        line = LineData(data=np.array([1.0, 2.0, 3.0]), x_axis=np.array([0.0, 0.5, 1.0]), x_unit="um", y_unit="nm")
        node.save(filename="profile", directory_path=tmpdir, format="CSV", value=line)
        csv_text = Path(tmpdir, "profile.csv").read_text(encoding="utf-8")
        assert "x,y,x_unit,y_unit" in csv_text
        assert "um" in csv_text and "nm" in csv_text
        node.save(filename="profile_npz", directory_path=tmpdir, format="NPZ", value=line)
        line_npz = np.load(Path(tmpdir, "profile_npz.npz"))
        assert np.allclose(line_npz["x"], line.x_axis)
        assert np.allclose(line_npz["y"], line.data)
        node.save(filename="profile_json", directory_path=tmpdir, format="JSON", value=line)
        line_json = json.loads(Path(tmpdir, "profile_json.json").read_text(encoding="utf-8"))
        assert line_json["x_unit"] == "um"
        assert line_json["y_unit"] == "nm"
        assert line_json["x"] == [0.0, 0.5, 1.0]
        assert line_json["y"] == [1.0, 2.0, 3.0]

        field = DataField(
            data=np.array([[1.0, 2.0], [3.0, 4.5]], dtype=np.float64),
            xreal=2e-6, yreal=1e-6, si_unit_xy="m", si_unit_z="m", colormap="viridis",
        )
        node.save(filename="field_tiff", directory_path=tmpdir, format="TIFF", value=field)
        field_tiff = tifffile.imread(Path(tmpdir, "field_tiff.tiff"))
        assert field_tiff.shape == field.data.shape
        assert field_tiff.dtype == np.float32
        assert np.allclose(field_tiff, field.data.astype(np.float32))

        node.save(filename="field_png", directory_path=tmpdir, format="PNG", value=field)
        field_png = np.asarray(PILImage.open(Path(tmpdir, "field_png.png")))
        assert field_png.shape == (2, 2, 3)
        assert field_png.dtype == np.uint8

        node.save(filename="field_npz", directory_path=tmpdir, format="NPZ", value=field)
        field_npz = np.load(Path(tmpdir, "field_npz.npz"))
        assert np.allclose(field_npz["field"], field.data)

        image = np.array([[[255, 0, 0], [0, 255, 0]], [[0, 0, 255], [255, 255, 0]]], dtype=np.uint8)
        node.save(filename="image_png", directory_path=tmpdir, format="PNG", value=image)
        image_png = np.asarray(PILImage.open(Path(tmpdir, "image_png.png")))
        assert image_png.shape == image.shape
        assert np.array_equal(image_png, image)

        node.save(filename="image_tiff", directory_path=tmpdir, format="TIFF", value=image)
        image_tiff = tifffile.imread(Path(tmpdir, "image_tiff.tiff"))
        assert image_tiff.shape == image.shape
        assert image_tiff.dtype == np.uint8
        assert np.array_equal(image_tiff, image)

        node.save(filename="image_npz", directory_path=tmpdir, format="NPZ", value=image)
        image_npz = np.load(Path(tmpdir, "image_npz.npz"))
        assert np.array_equal(image_npz["image"], image)

        annotation_image = ImageData(image, metadata={"annotation_context": {"si_unit_xy": "um", "si_unit_z": "nm"}})
        node.save(filename="annotation_png", directory_path=tmpdir, format="PNG", value=annotation_image)
        assert np.array_equal(np.asarray(PILImage.open(Path(tmpdir, "annotation_png.png"))), image)

        node.save(filename="annotation_tiff", directory_path=tmpdir, format="TIFF", value=annotation_image)
        assert np.array_equal(tifffile.imread(Path(tmpdir, "annotation_tiff.tiff")), image)

        node.save(filename="annotation_npz", directory_path=tmpdir, format="NPZ", value=annotation_image)
        assert np.array_equal(np.load(Path(tmpdir, "annotation_npz.npz"))["image"], image)

        measure_table = RecordTable([
            {"quantity": "Rq", "value": 1.23, "unit": "nm"},
            {"quantity": "Ra", "value": 0.98, "unit": "nm"},
        ])
        node.save(filename="measurements_csv", directory_path=tmpdir, format="CSV", value=measure_table)
        measure_csv = Path(tmpdir, "measurements_csv.csv").read_text(encoding="utf-8")
        assert "quantity,value,unit" in measure_csv
        assert "Rq,1.23,nm" in measure_csv
        node.save(filename="measurements_json", directory_path=tmpdir, format="JSON", value=measure_table)
        assert json.loads(Path(tmpdir, "measurements_json.json").read_text(encoding="utf-8")) == list(measure_table)

        record_table = DataTable([
            {"label": "particle-1", "height": 12.0, "area": 44.0},
            {"label": "particle-2", "height": 8.0, "area": 21.0},
        ])
        node.save(filename="records_csv", directory_path=tmpdir, format="CSV", value=record_table)
        record_csv = Path(tmpdir, "records_csv.csv").read_text(encoding="utf-8")
        assert "label,height,area" in record_csv
        assert "particle-1,12.0,44.0" in record_csv
        node.save(filename="records_json", directory_path=tmpdir, format="JSON", value=record_table)
        assert json.loads(Path(tmpdir, "records_json.json").read_text(encoding="utf-8")) == list(record_table)

        mesh = MeshModel(
            vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
            faces=np.array([[0, 1, 2]], dtype=np.int32),
        )
        node.save(filename="triangle", directory_path=tmpdir, format="OBJ", value=mesh)
        obj_text = Path(tmpdir, "triangle.obj").read_text(encoding="utf-8")
        assert "v 0.0 0.0 0.0" in obj_text
        assert "f 1 2 3" in obj_text

        node.save(filename="triangle", directory_path=tmpdir, format="STL", value=mesh)
        stl_text = Path(tmpdir, "triangle.stl").read_text(encoding="utf-8")
        assert stl_text.startswith("solid tono")
        assert "facet normal" in stl_text

        try:
            node.save(filename="triangle", directory_path=tmpdir, format="PNG", value=mesh)
            assert False, "Mesh should only be saveable as OBJ or STL"
        except ValueError:
            pass

        try:
            node.save(filename="field_bad", directory_path=tmpdir, format="CSV", value=field)
            assert False, "DATA_FIELD should reject unsupported save formats"
        except ValueError:
            pass

        # 1-D ndarray → _save_line path
        arr_1d = np.array([1.0, 2.0, 3.0])
        node.save(filename="line_1d", directory_path=tmpdir, format="CSV", value=arr_1d)
        assert Path(tmpdir, "line_1d.csv").exists()

        # Unsupported input type
        try:
            node.save(filename="bad_type", directory_path=tmpdir, format="JSON", value=object())
            assert False, "Expected ValueError for unsupported type"
        except ValueError:
            pass

        # Unsupported IMAGE format
        try:
            node.save(filename="img_bad", directory_path=tmpdir, format="JSON", value=image)
            assert False, "Expected ValueError for IMAGE + JSON"
        except ValueError:
            pass

        # Unsupported LINE format
        try:
            node.save(filename="line_bad", directory_path=tmpdir, format="TIFF", value=line)
            assert False, "Expected ValueError for LINE + TIFF"
        except ValueError:
            pass

        # Unsupported table format
        try:
            node.save(filename="table_bad", directory_path=tmpdir, format="TIFF", value=list(measure_table))
            assert False, "Expected ValueError for table + TIFF"
        except ValueError:
            pass

        # Unsupported scalar format
        try:
            node.save(filename="scalar_bad", directory_path=tmpdir, format="NPZ", value=3.14)
            assert False, "Expected ValueError for scalar + NPZ"
        except ValueError:
            pass


def test_save_no_filename():
    from backend.nodes.save import Save
    import tempfile
    node = Save()
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            node.save(filename="", directory_path=tmpdir, format="JSON", value=1.0)
            assert False, "Expected ValueError for empty filename"
        except ValueError:
            pass
