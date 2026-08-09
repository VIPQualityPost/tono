# Auto-import all node modules to trigger @register_node decorators.
import importlib
import pkgutil
import sys

_module_names = [_name for _finder, _name, _ispkg in pkgutil.iter_modules(__path__)]

if getattr(sys, "frozen", False) and not _module_names:
    raise RuntimeError(
        "No node modules found in frozen bundle: the build must include "
        "backend/nodes as data (see scripts/build-*.sh/ps1)."
    )

for _name in _module_names:
    importlib.import_module(f"{__name__}.{_name}")
