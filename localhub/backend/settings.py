from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import SETTINGS_PATH

DEFAULT_SETTINGS = {
    "role": "master",
    "auto_sync": True,
    "language": "ru",
    "device_name": "",
    "favorites": [],
    "trusted_devices": [],
    "last_sync": None,
}


def _read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


@dataclass
class LocalHubSettings:
    role: str = "master"
    auto_sync: bool = True
    language: str = "ru"
    device_name: str = ""
    favorites: list[str] = field(default_factory=list)
    trusted_devices: list[str] = field(default_factory=list)
    last_sync: str | None = None

    @classmethod
    def load(cls) -> "LocalHubSettings":
        raw = _read_json(SETTINGS_PATH, DEFAULT_SETTINGS)
        return cls(
            role=raw.get("role", DEFAULT_SETTINGS["role"]),
            auto_sync=raw.get("auto_sync", DEFAULT_SETTINGS["auto_sync"]),
            language=raw.get("language", DEFAULT_SETTINGS["language"]),
            device_name=raw.get("device_name", DEFAULT_SETTINGS["device_name"]),
            favorites=raw.get("favorites", DEFAULT_SETTINGS["favorites"]),
            trusted_devices=raw.get("trusted_devices", DEFAULT_SETTINGS["trusted_devices"]),
            last_sync=raw.get("last_sync", DEFAULT_SETTINGS["last_sync"]),
        )

    def save(self) -> None:
        data = {
            "role": self.role,
            "auto_sync": self.auto_sync,
            "language": self.language,
            "device_name": self.device_name,
            "favorites": self.favorites,
            "trusted_devices": self.trusted_devices,
            "last_sync": self.last_sync,
        }
        _write_json(SETTINGS_PATH, data)

    def add_favorite(self, path: str) -> None:
        if path not in self.favorites:
            self.favorites.append(path)
            self.save()

    def remove_favorite(self, path: str) -> None:
        if path in self.favorites:
            self.favorites.remove(path)
            self.save()
