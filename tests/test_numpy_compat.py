import backend  # noqa: F401
import numpy as np


def test_numpy_compat_aliases_are_available_after_backend_import():
    assert np.complex is complex
    assert np.float is float
    assert np.int is int
