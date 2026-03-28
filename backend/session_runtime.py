from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from backend.runtime_paths import app_data_dir, demo_dir

SESSION_HEADER = "X-Argonode-Session"
SESSION_QUERY = "session"
SESSION_URI_PREFIX = "session://uploads/"

PATH_INPUT_TYPES = {"FILE_PICKER", "FILE_PATH", "FOLDER_PICKER", "DIRECTORY"}

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$")


def validate_session_id(session_id: str) -> str:
    text = str(session_id or "").strip()
    if not _SESSION_ID_RE.fullmatch(text):
        raise ValueError("Invalid session id")
    return text


def session_root_dir(session_id: str) -> Path:
    validated = validate_session_id(session_id)
    return app_data_dir() / "sessions" / validated


def session_input_dir(session_id: str) -> Path:
    return session_root_dir(session_id) / "input"


def session_output_dir(session_id: str) -> Path:
    return session_root_dir(session_id) / "output"


def ensure_session_runtime_dirs(session_id: str) -> tuple[Path, Path]:
    input_path = session_input_dir(session_id)
    output_path = session_output_dir(session_id)
    input_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)
    return input_path, output_path


def normalize_relative_upload_path(raw_path: str) -> PurePosixPath:
    raw_text = str(raw_path or "").replace("\\", "/").strip()
    if not raw_text:
        raise ValueError("Missing upload path")

    path = PurePosixPath(raw_text)
    if path.is_absolute():
        raise ValueError("Upload paths must be relative")

    parts: list[str] = []
    for part in path.parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError("Upload paths cannot escape the session directory")
        if "\x00" in part:
            raise ValueError("Upload paths cannot contain NUL bytes")
        parts.append(part)

    if not parts:
        raise ValueError("Upload paths must contain at least one path segment")

    return PurePosixPath(*parts)


def session_upload_uri(relative_path: str | PurePosixPath) -> str:
    normalized = normalize_relative_upload_path(str(relative_path))
    return f"{SESSION_URI_PREFIX}{normalized.as_posix()}"


def session_uri_to_relative_path(value: str) -> PurePosixPath | None:
    text = str(value or "").strip()
    if not text.startswith(SESSION_URI_PREFIX):
        return None
    return normalize_relative_upload_path(text[len(SESSION_URI_PREFIX):])


def is_path_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def server_path_to_client_path(path_value: str | Path, session_id: str) -> str:
    path = Path(path_value).expanduser().resolve(strict=False)
    session_input = session_input_dir(session_id).resolve(strict=False)
    if is_path_within(session_input, path):
        rel = path.relative_to(session_input)
        return session_upload_uri(rel.as_posix())
    return str(path)


def resolve_client_path(
    value: str,
    *,
    session_id: str,
    allow_local_filesystem: bool,
) -> Path:
    text = str(value or "").strip()
    if not text:
        return Path("")

    rel = session_uri_to_relative_path(text)
    if rel is not None:
        return (session_input_dir(session_id) / Path(rel.as_posix())).resolve(strict=False)

    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        demo_candidate = (demo_dir() / text).expanduser().resolve(strict=False)
        if demo_candidate.exists():
            return demo_candidate

    if not candidate.is_absolute():
        if allow_local_filesystem:
            return candidate.resolve(strict=False)
        raise PermissionError("Browser sessions may only use files uploaded through Browse.")

    resolved = candidate.resolve(strict=False)
    if allow_local_filesystem:
        return resolved

    session_root = session_root_dir(session_id).resolve(strict=False)
    if is_path_within(session_root, resolved):
        return resolved

    raise PermissionError("Path is outside the current session workspace.")
