"""Tests for scripts/set_version.py — release-tag to pyproject.toml sync."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PYPROJECT_SAMPLE = """\
[project]
name = "tono"
version = "0.1.0"
dependencies = ["numpy"]
"""

SET_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "set_version.py"


def _run_set(tmp_path, content, *args):
    target = tmp_path / "pyproject.toml"
    target.write_text(content, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SET_SCRIPT), "--pyproject", str(target), *args],
        capture_output=True,
        text=True,
    )
    return result, target


def test_sets_exact_version(tmp_path):
    result, target = _run_set(tmp_path, PYPROJECT_SAMPLE, "1.2.0")
    assert result.returncode == 0
    assert result.stdout.strip() == "1.2.0"
    assert 'version = "1.2.0"' in target.read_text()


def test_strips_leading_v(tmp_path):
    result, target = _run_set(tmp_path, PYPROJECT_SAMPLE, "v3.4.5")
    assert result.returncode == 0
    assert result.stdout.strip() == "3.4.5"
    assert 'version = "3.4.5"' in target.read_text()


def test_preserves_rest_of_file(tmp_path):
    result, target = _run_set(tmp_path, PYPROJECT_SAMPLE, "v1.1.0")
    assert result.returncode == 0
    text = target.read_text()
    assert 'name = "tono"' in text
    assert 'dependencies = ["numpy"]' in text


def test_rejects_garbage_version(tmp_path):
    result, _ = _run_set(tmp_path, PYPROJECT_SAMPLE, "banana")
    assert result.returncode != 0
    assert 'version = "0.1.0"' in (tmp_path / "pyproject.toml").read_text()


def test_fails_without_version_line(tmp_path):
    result, _ = _run_set(tmp_path, '[project]\nname = "tono"\n', "1.2.0")
    assert result.returncode != 0
