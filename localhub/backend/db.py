from __future__ import annotations
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import DB_PATH


class Database:
    def __init__(self) -> None:
        self.path = DB_PATH
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                current_version_id INTEGER,
                deleted INTEGER DEFAULT 0,
                favorite INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL,
                version INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                author TEXT NOT NULL,
                checksum TEXT NOT NULL,
                comment TEXT,
                content_path TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL,
                sender_device TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                comment TEXT,
                action TEXT NOT NULL,
                payload_path TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                device_id TEXT,
                details TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                ip TEXT,
                trusted INTEGER DEFAULT 0,
                public_key TEXT,
                paired_at TEXT
            )
            """
        )
        self.connection.commit()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
        return cursor

    def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def create_file_record(self, path: str, created_at: str) -> int:
        cursor = self.execute(
            "INSERT OR IGNORE INTO files (path, created_at) VALUES (?, ?)",
            (path, created_at),
        )
        return cursor.lastrowid

    def ensure_file_record(self, path: str, created_at: str) -> None:
        self.create_file_record(path, created_at)

    def update_file(self, path: str, current_version_id: int, deleted: int = 0) -> None:
        self.ensure_file_record(path, created_at=datetime.utcnow().isoformat())
        self.execute(
            "UPDATE files SET current_version_id = ?, deleted = ?, created_at = created_at WHERE path = ?",
            (current_version_id, deleted, path),
        )

    def set_file_deleted(self, path: str, deleted: bool) -> None:
        self.execute(
            "UPDATE files SET deleted = ? WHERE path = ?",
            (1 if deleted else 0, path),
        )

    def set_favorite(self, path: str, favorite: bool) -> None:
        self.execute(
            "UPDATE files SET favorite = ? WHERE path = ?",
            (1 if favorite else 0, path),
        )

    def insert_version(
        self,
        file_path: str,
        version: int,
        timestamp: str,
        author: str,
        checksum: str,
        comment: str,
        content_path: str,
    ) -> int:
        cursor = self.execute(
            "INSERT INTO versions (file_path, version, timestamp, author, checksum, comment, content_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (file_path, version, timestamp, author, checksum, comment, content_path),
        )
        return cursor.lastrowid

    def insert_proposal(
        self,
        file_path: str,
        sender_device: str,
        status: str,
        comment: str,
        action: str,
        payload_path: str,
        timestamp: str,
    ) -> int:
        cursor = self.execute(
            "INSERT INTO proposals (file_path, sender_device, timestamp, status, comment, action, payload_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (file_path, sender_device, timestamp, status, comment, action, payload_path),
        )
        return cursor.lastrowid

    def insert_event(self, event_type: str, description: str, device_id: str | None = None, details: str | None = None) -> int:
        timestamp = datetime.utcnow().isoformat()
        cursor = self.execute(
            "INSERT INTO events (event_type, description, timestamp, device_id, details) VALUES (?, ?, ?, ?, ?)",
            (event_type, description, timestamp, device_id, details),
        )
        return cursor.lastrowid

    def insert_device(self, device_id: str, name: str, ip: str | None, trusted: bool, public_key: str | None, paired_at: str | None) -> None:
        self.execute(
            "INSERT OR REPLACE INTO devices (device_id, name, ip, trusted, public_key, paired_at) VALUES (?, ?, ?, ?, ?, ?)",
            (device_id, name, ip or "", 1 if trusted else 0, public_key or "", paired_at),
        )

    def query(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return self.fetchall(query, params)
