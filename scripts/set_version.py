"""Set the version in pyproject.toml to an exact value.

Usage: set_version.py [--pyproject PATH] VERSION

Accepts "v1.2.0" or "1.2.0" (a leading ``v`` is stripped), rewrites the
``version = "..."`` line in pyproject.toml in place preserving all other
formatting, and prints the normalized version (no ``v`` prefix).

Used by .github/workflows/version-sync.yml when a GitHub release is published,
so the package version on main tracks the tag that was cut.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_VERSION_RE = re.compile(r'^version = "[^"]+"', re.MULTILINE)
_VERSION_FORMAT = re.compile(r"v?\d+\.\d+\.\d+")


def set_version(text: str, version: str) -> str:
    """Return *text* with the version line replaced by *version*."""
    if not _VERSION_FORMAT.fullmatch(version):
        raise ValueError(f"not a supported version (expected v1.2.0 or 1.2.0): {version!r}")
    normalized = version.lstrip("vV")
    if _VERSION_RE.search(text) is None:
        raise ValueError('no `version = "..."` line found in pyproject.toml')
    return _VERSION_RE.sub(f'version = "{normalized}"', text, count=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", type=Path, default=None, help="pyproject.toml path (default: repo root)")
    parser.add_argument("version", help='version to set, e.g. "v1.2.0"')
    args = parser.parse_args()

    target = args.pyproject or (Path(__file__).resolve().parent.parent / "pyproject.toml")
    updated = set_version(target.read_text(encoding="utf-8"), args.version)
    target.write_text(updated, encoding="utf-8")
    print(args.version.lstrip("vV"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
