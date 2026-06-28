from __future__ import annotations
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import WORKSPACE_DIR
from .db import Database
from .storage import StorageManager
from .versioning import VersionManager


class WorkspaceChangeHandler(FileSystemEventHandler):
    def __init__(self, storage: StorageManager, version_manager: VersionManager, db: Database, on_change: Callable[[str], None]) -> None:
        self.storage = storage
        self.version_manager = version_manager
        self.db = db
        self.on_change = on_change

    def _generate_event(self, file_path: Path, event_type: str) -> None:
        relative = str(file_path.relative_to(WORKSPACE_DIR)).replace("\\", "/")
        self.db.insert_event(
            event_type=event_type,
            description=f"Файл {relative} был изменён",
            device_id=None,
            details=relative,
        )
        self.on_change(relative)

    def on_created(self, event):
        if event.is_directory:
            return
        self._generate_event(Path(event.src_path), "file_created")

    def on_modified(self, event):
        if event.is_directory:
            return
        self._generate_event(Path(event.src_path), "file_modified")

    def on_deleted(self, event):
        if event.is_directory:
            return
        relative = str(Path(event.src_path).relative_to(WORKSPACE_DIR)).replace("\\", "/")
        self.db.set_file_deleted(relative, True)
        self.db.insert_event(
            event_type="file_deleted",
            description=f"Файл {relative} перемещён в корзину",
            device_id=None,
            details=relative,
        )
        self.on_change(relative)


class SyncManager:
    def __init__(self, db: Database, storage: StorageManager, version_manager: VersionManager) -> None:
        self.db = db
        self.storage = storage
        self.version_manager = version_manager
        self.observer: Observer | None = None
        self.thread: threading.Thread | None = None
        self.running = False

    def _on_workspace_change(self, relative_path: str) -> None:
        if not Path(WORKSPACE_DIR / relative_path).exists():
            return
        try:
            self.version_manager.create_version(relative_path, author="local", comment="Авто-синхронизация")
        except Exception:
            pass

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.observer = Observer()
        handler = WorkspaceChangeHandler(self.storage, self.version_manager, self.db, self._on_workspace_change)
        self.observer.schedule(handler, str(WORKSPACE_DIR), recursive=True)
        self.observer.start()

    def stop(self) -> None:
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.running = False

    def manual_sync(self) -> None:
        self.db.insert_event(
            event_type="sync_requested",
            description="Пользователь запросил синхронизацию",
            device_id=None,
            details=None,
        )
