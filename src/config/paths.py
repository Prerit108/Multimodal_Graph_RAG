"""Filesystem paths for user uploads. Directories are created on demand."""
from __future__ import annotations
import os
from pathlib import Path


def upload_dir() -> str:
    """UPLOAD_DIR, created if missing (streamlit/api/smoke all land here)."""
    from src.config.settings import get_settings
    d = get_settings().UPLOAD_DIR
    os.makedirs(d, exist_ok=True)
    return d


def upload_path(filename: str) -> str:
    """Resolve an uploaded filename inside UPLOAD_DIR, sanitised against traversal."""
    name = (filename or "").replace("\\", "/").strip()
    safe = Path(name).name.strip() or "upload"
    return str(Path(upload_dir()) / safe)