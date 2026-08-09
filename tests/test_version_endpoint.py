"""Tests for the /version endpoint: git-tag-derived version + commit hash."""

from __future__ import annotations

import asyncio
import json
import re

from backend.server import _describe_git_version, _get_git_hash, _get_git_version, create_app


def test_git_hash_is_sha1_or_none():
    # None is legitimate: packaged desktop builds have no .git at runtime.
    h = _get_git_hash()
    assert h is None or re.fullmatch(r"[0-9a-f]{40}", h)


def test_git_version_never_empty():
    # In a checkout with no reachable tags this resolves to the package version;
    # otherwise it is a git describe string (e.g. "v1.1.0" or "v1.1.0-2-g4791a2c").
    v = _get_git_version()
    assert isinstance(v, str) and v.strip()


def test_describe_hides_bare_hash():
    # git describe --always falls back to the short hash when no tag is reachable;
    # that must not be presented as a human-readable version.
    v = _describe_git_version()
    assert v is None or not re.fullmatch(r"[0-9a-f]{4,40}(?:-dirty)?", v)


def test_baked_version_file_takes_precedence(tmp_path, monkeypatch):
    baked = tmp_path / "build_version.txt"
    baked.write_text("v1.1.0", encoding="utf-8")
    monkeypatch.setattr("backend.server._APP_GIT_VERSION", None)
    monkeypatch.setattr("backend.runtime_paths.resource_root", lambda: tmp_path)
    assert _get_git_version() == "v1.1.0"


def test_bare_hash_bake_falls_through(tmp_path, monkeypatch):
    baked = tmp_path / "build_version.txt"
    baked.write_text("4791a2c-dirty", encoding="utf-8")
    monkeypatch.setattr("backend.server._APP_GIT_VERSION", None)
    monkeypatch.setattr("backend.runtime_paths.resource_root", lambda: tmp_path)
    assert _get_git_version().strip()


def _version_route():
    app = create_app(asyncio.new_event_loop())
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        if resource is not None and getattr(resource, "canonical", None) == "/version":
            return route
    return None


def test_version_route_registered():
    assert _version_route() is not None


def test_version_payload_shape():
    route = _version_route()
    assert route is not None
    response = asyncio.run(route.handler(None))
    assert response.status == 200
    payload = json.loads(response.body)
    assert isinstance(payload["version"], str) and payload["version"]
    assert payload["git_hash"] is None or re.fullmatch(r"[0-9a-f]{40}", payload["git_hash"])
