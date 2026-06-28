from __future__ import annotations
from datetime import datetime
from pathlib import Path
import hashlib

from .db import Database
from .storage import StorageManager


class VersionManager:
    def __init__(self, db: Database, storage: StorageManager) -> None:
        self.db = db
        self.storage = storage

    def _checksum(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def create_version(self, file_path: str, author: str, comment: str | None = "") -> int:
        workspace_path = self.storage.workspace_path(file_path)
        if not workspace_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        checksum = self._checksum(workspace_path.read_bytes())
        existing_versions = self.db.fetchall(
            "SELECT version FROM versions WHERE file_path = ? ORDER BY version DESC LIMIT 1",
            (file_path,),
        )
        next_version = 1
        if existing_versions:
            next_version = existing_versions[0]["version"] + 1
        timestamp = datetime.utcnow().isoformat()
        version_id = self.db.insert_version(
            file_path=file_path,
            version=next_version,
            timestamp=timestamp,
            author=author,
            checksum=checksum,
            comment=comment or "",
            content_path=str(self.storage.copy_to_version_store(workspace_path, next_version, checksum)),
        )
        self.db.update_file(file_path, version_id)
        self.db.insert_event(
            event_type="version_created",
            description=f"Новая версия файла {file_path} создана {author}",
            device_id=author,
            details=f"version={next_version} checksum={checksum}",
        )
        return version_id

    def get_history(self, limit: int = 100) -> list[dict[str, str | int]]:
        rows = self.db.fetchall(
            "SELECT id, file_path, version, timestamp, author, checksum, comment, content_path FROM versions ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in rows]

    def restore_version(self, version_id: int) -> dict[str, str | int]:
        row = self.db.fetchone("SELECT * FROM versions WHERE id = ?", (version_id,))
        if not row:
            raise ValueError("Version not found")
        source = Path(row["content_path"])
        destination = self.storage.workspace_path(row["file_path"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        self.db.insert_event(
            event_type="version_restored",
            description=f"Файл {row['file_path']} восстановлен до версии {row['version']}",
            device_id=row["author"],
            details=f"version_id={version_id}",
        )
        return dict(row)
