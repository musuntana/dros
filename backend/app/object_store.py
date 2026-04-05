from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID, uuid4

from .settings import get_settings

OBJECT_URI_PREFIX = "object://"
UPLOAD_PREFIX = "uploads"
EXPORT_PREFIX = "exports"


def get_object_store_root() -> Path:
    root = get_settings().object_store_path
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_upload_object_key(filename: str) -> str:
    safe_filename = _sanitize_filename(filename)
    return f"{UPLOAD_PREFIX}/{uuid4()}/{safe_filename}"


def build_export_object_key(manuscript_id: UUID, export_format: str) -> str:
    return f"{EXPORT_PREFIX}/{manuscript_id}/{uuid4()}.{export_format}"


def storage_uri_for_key(object_key: str) -> str:
    return f"{OBJECT_URI_PREFIX}{normalize_object_key(object_key)}"


def object_key_to_path(object_key: str) -> Path:
    root = get_object_store_root()
    normalized = normalize_object_key(object_key)
    path = (root / normalized).resolve()
    if not _is_relative_to(path, root.resolve()):
        raise ValueError("object_key resolves outside configured object store root")
    return path


def resolve_storage_uri(storage_uri: str) -> Path | None:
    if not storage_uri.startswith(OBJECT_URI_PREFIX):
        return None
    return object_key_to_path(storage_uri.removeprefix(OBJECT_URI_PREFIX))


def write_object_bytes(object_key: str, payload: bytes) -> Path:
    path = object_key_to_path(object_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def normalize_object_key(object_key: str) -> str:
    candidate = object_key.strip().lstrip("/")
    if candidate == "":
        raise ValueError("object_key must not be empty")
    normalized = str(Path(candidate))
    if normalized in {".", ""} or normalized.startswith("../") or normalized == "..":
        raise ValueError("object_key must stay within object store root")
    return normalized.replace("\\", "/")


def _sanitize_filename(filename: str) -> str:
    candidate = filename.strip() or "upload.bin"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(candidate).name).strip("-.")
    return safe or "upload.bin"


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

