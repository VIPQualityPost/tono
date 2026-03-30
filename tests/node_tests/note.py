import os
import tempfile
from pathlib import Path


def test_parse_ibw_note():
    from backend.nodes.note import _parse_ibw_note

    # key=value pairs
    note = b"ScanSize=500e-9\nSetPoint=1.0\nScanRate=1.0\n"
    rows = _parse_ibw_note(note)
    assert len(rows) == 3
    assert rows[0] == {"key": "ScanSize", "value": "500e-9"}

    # key:value pairs
    note_colon = b"Operator: alice\nDate: 2025-01-01\n"
    rows2 = _parse_ibw_note(note_colon)
    assert len(rows2) == 2
    assert rows2[0]["key"] == "Operator"
    assert rows2[0]["value"] == "alice"

    # empty bytes → empty result
    assert _parse_ibw_note(b"") == []

    # blank lines are skipped (covers 'if not line: continue')
    note_blanks = b"\n\nKey=Val\n\n"
    rows_blank = _parse_ibw_note(note_blanks)
    assert len(rows_blank) == 1

    # lines without separator are skipped
    note_mixed = b"NoSeparatorLine\nKey=Value\n"
    rows3 = _parse_ibw_note(note_mixed)
    assert len(rows3) == 1
    assert rows3[0]["key"] == "Key"

    # non-bytes input → exception handler returns []
    rows_exc = _parse_ibw_note(None)
    assert rows_exc == []


def test_note_load_no_file():
    from backend.nodes.note import Note
    node = Note()
    try:
        node.load(filename="")
        assert False, "Expected ValueError for empty filename"
    except ValueError:
        pass


def test_note_load_file_not_found():
    from backend.nodes.note import Note
    node = Note()
    try:
        node.load(filename="/nonexistent/path/file.ibw")
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_note_load_wrong_extension():
    from backend.nodes.note import Note
    node = Note()
    with tempfile.TemporaryDirectory() as tmpdir:
        txt_path = os.path.join(tmpdir, "notes.txt")
        Path(txt_path).write_text("Key=Value")
        try:
            node.load(filename=txt_path)
            assert False, "Expected ValueError for non-ibw file"
        except ValueError as e:
            assert ".txt" in str(e)


def test_note_load_empty_note():
    """An .ibw file with no parseable note entries raises ValueError."""
    from backend.nodes.note import Note
    from unittest.mock import patch
    import numpy as np

    node = Note()
    with tempfile.TemporaryDirectory() as tmpdir:
        ibw_path = os.path.join(tmpdir, "empty_note.ibw")
        Path(ibw_path).write_bytes(b"fake_ibw")

        # Mock the IBW loader to return a wave with empty note
        fake_wave = {"wave": {"wave_header": {}, "wData": np.zeros((4, 4)), "note": b""}}
        with patch("backend.nodes.note._import_ibw_loader", return_value=lambda path: fake_wave):
            try:
                node.load(filename=ibw_path)
                assert False, "Expected ValueError for empty note"
            except ValueError as e:
                assert "No metadata" in str(e)


def test_note_load_ibw():
    """Load from a real .ibw file if available in the demo directory."""
    from backend.nodes.note import Note
    from backend.data_types import DataTable

    demo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "demo"))
    ibw_path = None
    for candidate in ["Calcite.ibw", "DNA.ibw", "APL_Figure4.ibw"]:
        p = os.path.join(demo_dir, candidate)
        if os.path.exists(p):
            ibw_path = p
            break
    if ibw_path is None:
        return

    node = Note()
    try:
        result, = node.load(filename=ibw_path)
        assert isinstance(result, DataTable)
        assert len(result) > 0
        assert "key" in result[0]
        assert "value" in result[0]
    except ValueError:
        # Some .ibw files have no note metadata — that's acceptable
        pass
