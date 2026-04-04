# Auto-import all node modules to trigger @register_node decorators.
import importlib
import pkgutil

for _finder, _name, _ispkg in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{_name}")
