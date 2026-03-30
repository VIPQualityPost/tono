from pathlib import Path
import pytest

_DIR = Path(__file__).parent


def pytest_collect_file(parent, file_path):
    """Collect all non-private .py files in this directory as test modules.

    Allows test files to be named after their source module (e.g. acf_2d.py)
    rather than requiring a test_ prefix.
    """
    if (
        file_path.parent == _DIR
        and file_path.suffix == ".py"
        and not file_path.name.startswith("_")
        and file_path.name != "conftest.py"
    ):
        return pytest.Module.from_parent(parent, path=file_path)
