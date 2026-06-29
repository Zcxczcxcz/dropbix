from __future__ import annotations
import os
from pathlib import Path
from typing import Iterable

from .config import ARCHIVE_DIR, MAX_ARCHIVE_BYTES
from .db import Database


class ArchiveManager:
    def __init__(self, db: Database) -> None:
        self.db = db

    def archive_event(self, event_type: str, description: str, details: str | None = None) -> int:
        return self.db.insert_event(event_type=event_type, description=description, device_id=None, details=details)

    def current_archive_size(self) -> int:
        total = 0
        for root, _, files in os.walk(ARCHIVE_DIR):
            for name in files:
                total += os.path.getsize(Path(root) / name)
        return total

    def enforce_size_limit(self) -> None:
        if not ARCHIVE_DIR.exists():
            return
        entries = sorted(
            (path for path in ARCHIVE_DIR.glob("**/*") if path.is_file()),
            key=lambda item: item.stat().st_mtime,
        )
        while self.current_archive_size() > MAX_ARCHIVE_BYTES and entries:
            oldest = entries.pop(0)
            oldest.unlink()
            self.db.insert_event(
                event_type="archive_pruned",
                description=f"Старые архивные данные удалены: {oldest.name}",
                device_id=None,
                details=str(oldest),
            )

    def list_archive_files(self) -> list[str]:
        if not ARCHIVE_DIR.exists():
            return []
        return [str(path.relative_to(ARCHIVE_DIR)).replace('\\', '/') for path in ARCHIVE_DIR.rglob('*') if path.is_file()]

    def list_events(self, limit: int = 200) -> list[dict[str, str | None]]:
        rows = self.db.fetchall(
            "SELECT event_type, description, timestamp, details FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in rows]
