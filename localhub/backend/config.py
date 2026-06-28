from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

APP_NAME = "LocalHub"
DEFAULT_PORT = 8743
HTTP_PORT = 8743
UDP_BROADCAST_PORT = 48321
MAX_ARCHIVE_BYTES = 4 * 1024**3

APP_DATA_DIR = Path(os.environ.get("LOCALHUB_DATA_DIR", Path.home() / ".localhub"))
WORKSPACE_DIR = APP_DATA_DIR / "workspace"
STORAGE_DIR = APP_DATA_DIR / "storage"
VERSION_DIR = STORAGE_DIR / "versions"
PROPOSAL_DIR = STORAGE_DIR / "proposals"
TRASH_DIR = APP_DATA_DIR / "trash"
ARCHIVE_DIR = APP_DATA_DIR / "archive"
DB_PATH = APP_DATA_DIR / "localhub.db"
SETTINGS_PATH = APP_DATA_DIR / "settings.json"
DEVICES_PATH = APP_DATA_DIR / "devices.json"
IDENTITY_PATH = APP_DATA_DIR / "identity.key"


def ensure_directories() -> None:
    """Create the isolated application folders for data, storage, and archives."""
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    VERSION_DIR.mkdir(parents=True, exist_ok=True)
    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        with SETTINGS_PATH.open("w", encoding="utf-8") as handle:
            json.dump({}, handle)
