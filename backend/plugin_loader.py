"""
Plugin loader for tono.

Scans a plugins directory for .py files and packages (directories containing
__init__.py), imports each one, and lets their @register_node decorators
self-register into NODE_CLASS_MAPPINGS.  Errors are logged as warnings and
never crash the server.

Plugin authors write a single .py file dropped into the plugins/ directory:

    from backend.node_registry import register_node
    from backend.data_types import DataField

    @register_node(display_name="My Filter")
    class MyFilter:
        CATEGORY = "Plugins"

        @classmethod
        def INPUT_TYPES(cls):
            return {"required": {"field": ("DATA_FIELD",)}}

        OUTPUTS = (("DATA_FIELD", "result"),)
        FUNCTION = "process"

        def process(self, field: DataField) -> tuple:
            ...
            return (field.replace(data=result),)

Multi-file plugins: place a directory with __init__.py in the plugins folder.
Files and directories whose names start with '_' are skipped (private helpers).
"""
from __future__ import annotations

import importlib.util
import logging
import sys
import traceback
from pathlib import Path

log = logging.getLogger(__name__)


def load_plugins(plugins_dir: Path) -> list[tuple[str, str]]:
    """
    Import every plugin found in *plugins_dir*.

    Returns a list of ``(plugin_name, error_traceback)`` for each plugin that
    failed to load.  An empty list means all plugins loaded without error.
    Plugins that fail do not block subsequent plugins from loading.
    """
    if not plugins_dir.exists():
        return []

    candidates = _discover(plugins_dir)
    if not candidates:
        return []

    log.info("Loading plugins from %s", plugins_dir)
    errors: list[tuple[str, str]] = []

    for name, path in candidates:
        try:
            _import_plugin(name, path)
            log.info("Plugin loaded: %s", name)
        except Exception:
            msg = traceback.format_exc()
            log.warning("Plugin %r failed to load:\n%s", name, msg)
            errors.append((name, msg))

    return errors


def _discover(plugins_dir: Path) -> list[tuple[str, Path]]:
    """
    Return ``(name, path)`` pairs for every importable plugin entry.

    A plugin is either:
    - a ``.py`` file (excluding ``__init__.py`` and ``_``-prefixed files), or
    - a sub-directory that contains ``__init__.py`` (a package plugin).

    Both kinds must not have a leading ``_`` in their name so that private
    helper modules placed alongside plugins are not mistakenly imported.
    """
    found: list[tuple[str, Path]] = []
    for entry in sorted(plugins_dir.iterdir()):
        if entry.name.startswith("_"):
            continue
        if entry.is_file() and entry.suffix == ".py":
            found.append((entry.stem, entry))
        elif entry.is_dir() and (entry / "__init__.py").exists():
            found.append((entry.name, entry / "__init__.py"))
    return found


def _import_plugin(name: str, path: Path) -> None:
    """
    Import a single plugin file (or package ``__init__.py``) via importlib.

    The module is registered under ``tono_plugins.<name>`` in
    ``sys.modules``.  This namespace:
    - avoids collisions with any PyPI package of the same name, and
    - makes package-style plugins (with sub-modules) work correctly, because
      their relative imports resolve against the ``tono_plugins.*`` parent.

    If the module was previously imported (e.g. on a hot-reload call after an
    upload), it is deleted from ``sys.modules`` first so the file is re-executed
    and any updated ``@register_node`` decorators take effect.
    """
    module_name = f"tono_plugins.{name}"

    from backend.node_registry import module_registered_names, unregister_node

    # Drop everything this module registered on a previous load: the fresh
    # exec below re-registers surviving classes, while renamed or deleted
    # ones must not linger in the registry.
    for stale in module_registered_names(module_name):
        unregister_node(stale)

    # Remove stale module to support hot-reload after /upload-plugin.
    if module_name in sys.modules:
        del sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create a module spec for {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # @register_node decorators fire here
