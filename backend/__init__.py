from __future__ import annotations

import numpy as np


def _apply_numpy_compat_aliases() -> None:
    """Restore removed NumPy scalar aliases still used by some dependencies."""
    aliases = {
        "complex": complex,
        "float": float,
        "int": int,
    }
    for name, value in aliases.items():
        if not hasattr(np, name):
            setattr(np, name, value)


_apply_numpy_compat_aliases()
