from pathlib import Path

import pytest

from backend.server import PNG_SIGNATURE, save_png_bytes


def test_save_png_bytes_writes_exact_png_payload(tmp_path: Path):
    target = tmp_path / "workflow"
    payload = PNG_SIGNATURE + b"argonode-test-payload"

    saved_path = save_png_bytes(str(target), payload)

    assert saved_path == tmp_path / "workflow.png"
    assert saved_path.read_bytes() == payload


def test_save_png_bytes_rejects_invalid_payload(tmp_path: Path):
    with pytest.raises(ValueError, match="valid PNG"):
        save_png_bytes(str(tmp_path / "workflow.png"), b"not-a-png")
