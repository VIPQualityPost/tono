import os
from pathlib import Path

from backend.frontend_build import frontend_dist_is_stale


def _write_with_mtime(path: Path, content: str, timestamp: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.utime(path, (timestamp, timestamp))


def test_frontend_dist_is_stale_when_dist_is_missing(tmp_path: Path):
    frontend_dir = tmp_path / "frontend"
    dist_dir = frontend_dir / "dist"

    _write_with_mtime(frontend_dir / "src" / "main.jsx", "export default 1;", 200.0)

    assert frontend_dist_is_stale(frontend_dir, dist_dir) is True


def test_frontend_dist_is_stale_when_source_is_newer(tmp_path: Path):
    frontend_dir = tmp_path / "frontend"
    dist_dir = frontend_dir / "dist"

    _write_with_mtime(dist_dir / "index.html", "<html></html>", 100.0)
    _write_with_mtime(frontend_dir / "src" / "App.jsx", "export default 1;", 200.0)

    assert frontend_dist_is_stale(frontend_dir, dist_dir) is True


def test_frontend_dist_is_current_when_dist_is_newer(tmp_path: Path):
    frontend_dir = tmp_path / "frontend"
    dist_dir = frontend_dir / "dist"

    _write_with_mtime(frontend_dir / "src" / "App.jsx", "export default 1;", 100.0)
    _write_with_mtime(dist_dir / "assets" / "app.js", "console.log('ok');", 200.0)
    _write_with_mtime(dist_dir / "index.html", "<html></html>", 200.0)

    assert frontend_dist_is_stale(frontend_dir, dist_dir) is False
