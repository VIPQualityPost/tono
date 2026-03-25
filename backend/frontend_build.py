from __future__ import annotations

import logging
import os
import subprocess
import threading
from pathlib import Path

_BUILD_LOCK = threading.Lock()


class FrontendBuildError(RuntimeError):
    """Raised when the source frontend could not be rebuilt."""


def _latest_mtime(root: Path) -> float:
    if not root.exists():
        return 0.0
    return max(
        (path.stat().st_mtime for path in root.rglob("*") if path.is_file()),
        default=0.0,
    )


def source_frontend_mtime(frontend_dir: Path) -> float:
    tracked_files = (
        frontend_dir / "index.html",
        frontend_dir / "package.json",
        frontend_dir / "package-lock.json",
        frontend_dir / "vite.config.js",
    )
    mtimes = [path.stat().st_mtime for path in tracked_files if path.exists()]
    mtimes.append(_latest_mtime(frontend_dir / "src"))
    mtimes.append(_latest_mtime(frontend_dir / "public"))
    return max(mtimes, default=0.0)


def dist_frontend_mtime(dist_dir: Path) -> float:
    if not (dist_dir / "index.html").exists():
        return 0.0
    return _latest_mtime(dist_dir)


def frontend_dist_is_stale(frontend_dir: Path, dist_dir: Path) -> bool:
    return dist_frontend_mtime(dist_dir) < source_frontend_mtime(frontend_dir)


def _npm_executable() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _format_build_output(stdout: str, stderr: str) -> str:
    combined = "\n".join(part.strip() for part in (stdout, stderr) if part.strip())
    if not combined:
        return ""
    lines = combined.splitlines()
    if len(lines) > 40:
        lines = lines[-40:]
    return "\n".join(lines)


def _build_failure_hint(detail: str) -> str:
    if "spawn EPERM" not in detail:
        return ""
    return (
        "Windows note: this build hit `spawn EPERM`, which usually means the current Node.js "
        "install is not cooperating with esbuild. Node 20 LTS is the safest option here. "
        "After switching, run `npm --prefix frontend install` and try again."
    )


def ensure_frontend_dist_ready(
    project_root: Path,
    frontend_dir: Path,
    dist_dir: Path,
    logger: logging.Logger | None = None,
) -> bool:
    if not frontend_dist_is_stale(frontend_dir, dist_dir):
        return False

    with _BUILD_LOCK:
        if not frontend_dist_is_stale(frontend_dir, dist_dir):
            return False

        if logger is not None:
            logger.info("Frontend sources changed; rebuilding frontend/dist before serving the web app.")

        result = subprocess.run(
            [_npm_executable(), "run", "build"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = _format_build_output(result.stdout, result.stderr)
            message = (
                "Frontend build failed while refreshing frontend/dist. "
                "Run `npm run build` from the repo root to inspect the full error."
            )
            hint = _build_failure_hint(detail)
            if hint:
                message = f"{message}\n\n{hint}"
            if detail:
                message = f"{message}\n\n{detail}"
            raise FrontendBuildError(message)

        if not (dist_dir / "index.html").exists():
            raise FrontendBuildError(
                "Frontend rebuild finished, but frontend/dist/index.html is still missing."
            )

        if logger is not None:
            logger.info("Frontend rebuild complete.")

        return True
