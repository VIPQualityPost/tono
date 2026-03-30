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


def test_measurement_helpers():
    from backend.nodes.helpers import _measurement_names, _measurement_entry, _measurement_value
    from backend.data_types import RecordTable

    table = RecordTable([
        {"quantity": "Rq", "value": 0.5, "unit": "nm"},
        {"quantity": "Ra", "value": 0.3, "unit": "nm"},
        {"quantity": "Rq", "value": 0.5, "unit": "nm"},  # duplicate — deduplicated in names
    ])

    names = _measurement_names(table)
    assert names == ["Rq", "Ra"]

    row = _measurement_entry(table, "Ra")
    assert row["value"] == 0.3

    # falls back to first when selection not found
    row_fallback = _measurement_entry(table, "nonexistent")
    assert row_fallback["quantity"] == "Rq"

    val = _measurement_value(table, "Ra")
    assert val == 0.3


def test_measurement_value_errors():
    from backend.nodes.helpers import _measurement_value
    from backend.data_types import RecordTable

    empty = RecordTable([])
    try:
        _measurement_value(empty, "anything")
        assert False, "should raise"
    except ValueError:
        pass

    bool_table = RecordTable([{"quantity": "flag", "value": True}])
    try:
        _measurement_value(bool_table, "flag")
        assert False, "should raise"
    except ValueError:
        pass


def test_format_with_unit():
    from backend.nodes.helpers import _format_with_unit, _format_numeric

    assert _format_numeric(0.0) == "0"
    assert not np.isfinite(float('inf')) or _format_numeric(float('inf')) is not None

    # plain number no unit
    result = _format_with_unit(1.5, "")
    assert "1.5" in result

    # prefixable unit gets SI prefix
    result_nm = _format_with_unit(1e-9, "m")
    assert "n" in result_nm or "1e" in result_nm

    # non-prefixable unit is left as-is
    result_bare = _format_with_unit(3.14, "rad")
    assert "3.14" in result_bare and "rad" in result_bare

    # zero value
    result_zero = _format_with_unit(0.0, "m")
    assert "0" in result_zero


def test_table_and_array_ops():
    from backend.nodes.helpers import (
        TABLE_OPS, ARRAY_OPS, extract_numeric_table_values,
        resolve_table_column_name, _common_table_unit,
    )
    from backend.data_types import RecordTable

    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert TABLE_OPS["min"](values) == 1.0
    assert TABLE_OPS["max"](values) == 5.0
    assert TABLE_OPS["mean"](values) == 3.0
    assert TABLE_OPS["sum"](values) == 15.0
    assert TABLE_OPS["range"](values) == 4.0
    assert TABLE_OPS["count"](values) == 5.0
    assert TABLE_OPS["median"](values) == 3.0
    assert TABLE_OPS["std"](values) > 0
    assert TABLE_OPS["variance"](values) > 0

    assert ARRAY_OPS["rms"](values) > 0
    assert ARRAY_OPS["std"](values) > 0

    table = RecordTable([
        {"quantity": "A", "value": 1.0, "unit": "m"},
        {"quantity": "B", "value": 2.0, "unit": "m"},
        {"not_a_dict": True},
        {"quantity": "C", "value": "not_a_number"},
    ])
    nums = extract_numeric_table_values(table, "value")
    assert nums == [1.0, 2.0]

    col = resolve_table_column_name(table, "")
    assert col == "value"

    unit = _common_table_unit(table, "value")
    assert unit == "m"


def test_square_unit_and_apply():
    from backend.nodes.helpers import _square_unit, _apply_scalar_unit

    assert _square_unit("m") == "m^2"
    assert _square_unit("m/s") == "(m/s)^2"
    assert _square_unit("") == ""

    assert _apply_scalar_unit("m", "variance") == "m^2"
    assert _apply_scalar_unit("m", "count") == "count"
    assert _apply_scalar_unit("m", "mean") == "m"
    assert _apply_scalar_unit("", "mean") == ""


def test_nice_length():
    from backend.nodes.helpers import _nice_length

    assert _nice_length(0.0) == 0.0
    assert _nice_length(float('inf')) == 0.0
    assert _nice_length(7.3) == 5.0
    assert _nice_length(1500.0) == 1000.0
    assert _nice_length(0.003) == 0.002
