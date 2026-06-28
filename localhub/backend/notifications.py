from __future__ import annotations

from .db import Database


class NotificationManager:
    def __init__(self, db: Database) -> None:
        self.db = db

    def latest(self, limit: int = 50) -> list[dict[str, str]]:
        rows = self.db.fetchall(
            "SELECT event_type, description, timestamp, details FROM events ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in rows]

    def create_notification(self, event_type: str, description: str, details: str | None = None) -> int:
        return self.db.insert_event(event_type=event_type, description=description, device_id=None, details=details)
