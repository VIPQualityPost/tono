import numpy as np
from backend.data_types import DataField


def make_field(data=None, shape=(64, 64), xreal=1e-6, yreal=1e-6):
    """Create a DataField, optionally from given data or a random field."""
    if data is None:
        data = np.random.default_rng(42).standard_normal(shape)
    return DataField(data=data, xreal=xreal, yreal=yreal, si_unit_xy="m", si_unit_z="m")
