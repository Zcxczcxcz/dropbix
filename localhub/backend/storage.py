from __future__ import annotations
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .config import PROPOSAL_DIR, TRASH_DIR, VERSION_DIR, WORKSPACE_DIR
from .db import Database


class StorageManager:
    def __init__(self, db: Database) -> None:
        self.db = db

    def normalize_path(self, file_path: str) -> str:
        return str(Path(file_path).as_posix()).lstrip("/")

    def workspace_path(self, file_path: str) -> Path:
        normalized = self.normalize_path(file_path)
        return WORKSPACE_DIR / normalized

    def ensure_workspace(self) -> None:
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    def save_working_copy(self, source: Path, target_relative: str) -> Path:
        target = self.workspace_path(target_relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target

    def remove_file(self, file_path: str) -> None:
        path = self.workspace_path(file_path)
        if path.exists():
            path.unlink()

    def proposal_path(self, proposal_id: str) -> Path:
        path = PROPOSAL_DIR / proposal_id
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def move_to_trash(self, file_path: str) -> Path | None:
        path = self.workspace_path(file_path)
        if not path.exists():
            return None
        destination = TRASH_DIR / self.normalize_path(file_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), destination)
        return destination

    def restore_from_trash(self, file_path: str) -> Path | None:
        source = TRASH_DIR / self.normalize_path(file_path)
        if not source.exists():
            return None
        destination = self.workspace_path(file_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), destination)
        return destination

    def read_file(self, file_path: str) -> bytes | None:
        path = self.workspace_path(file_path)
        if path.exists():
            return path.read_bytes()
        return None

    def list_shared_files(self) -> list[str]:
        if not WORKSPACE_DIR.exists():
            return []
        return [str(path.relative_to(WORKSPACE_DIR)).replace('\\', '/') for path in WORKSPACE_DIR.rglob('*') if path.is_file()]

    def version_path(self, version_id: int, checksum: str) -> Path:
        suffix = checksum[:16]
        path = VERSION_DIR / f"version-{version_id}-{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def copy_to_version_store(self, source: Path, version_id: int, checksum: str) -> Path:
        destination = self.version_path(version_id, checksum)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination

    def list_trash(self) -> list[str]:
        if not TRASH_DIR.exists():
            return []
        return [str(path.relative_to(TRASH_DIR)).replace('\\', '/') for path in TRASH_DIR.rglob('*') if path.is_file()]

    def path_exists(self, file_path: str) -> bool:
        return self.workspace_path(file_path).exists()

    def checksum_path(self, path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open('rb') as handle:
            while chunk := handle.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def scan_workspace(self) -> list[str]:
        return self.list_shared_files()
