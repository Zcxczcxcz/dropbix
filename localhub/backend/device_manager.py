from __future__ import annotations
from datetime import datetime
from typing import Any

from .auth import IdentityManager
from .db import Database


class DeviceManager:
    def __init__(self, db: Database, identity: IdentityManager) -> None:
        self.db = db
        self.identity = identity
        self.discovered_devices: dict[str, dict[str, str]] = {}

    def register_discovered_device(self, device_id: str, name: str, ip: str, public_key: str | None = None) -> None:
        if device_id == self.identity.device_id():
            return
        self.discovered_devices[device_id] = {
            "device_id": device_id,
            "name": name,
            "ip": ip,
            "public_key": public_key or "",
            "trusted": "0",
        }
        self.db.insert_device(device_id=device_id, name=name, ip=ip, trusted=False, public_key=public_key, paired_at=datetime.utcnow().isoformat())

    def list_devices(self) -> list[dict[str, Any]]:
        rows = self.db.fetchall("SELECT device_id, name, ip, trusted, public_key, paired_at FROM devices")
        devices = [dict(row) for row in rows]
        for device_id, info in self.discovered_devices.items():
            if device_id not in {device["device_id"] for device in devices}:
                devices.append({
                    "device_id": info["device_id"],
                    "name": info["name"],
                    "ip": info["ip"],
                    "trusted": 0,
                    "public_key": info.get("public_key", ""),
                    "paired_at": None,
                })
        return devices

    def trust_device(self, device_id: str) -> None:
        row = self.db.fetchone("SELECT device_id, name, ip, public_key FROM devices WHERE device_id = ?", (device_id,))
        if not row:
            raise ValueError("Device not known")
        self.db.insert_device(
            device_id=row["device_id"],
            name=row["name"],
            ip=row["ip"],
            trusted=True,
            public_key=row["public_key"],
            paired_at=datetime.utcnow().isoformat(),
        )

    def untrust_device(self, device_id: str) -> None:
        row = self.db.fetchone("SELECT device_id, name, ip, public_key FROM devices WHERE device_id = ?", (device_id,))
        if not row:
            raise ValueError("Device not known")
        self.db.insert_device(
            device_id=row["device_id"],
            name=row["name"],
            ip=row["ip"],
            trusted=False,
            public_key=row["public_key"],
            paired_at=row["paired_at"],
        )

    def get_trusted_device_ids(self) -> list[str]:
        rows = self.db.fetchall("SELECT device_id FROM devices WHERE trusted = 1")
        return [row["device_id"] for row in rows]

    def manual_connect(self, device_id: str, name: str, ip: str, public_key: str | None = None) -> None:
        self.db.insert_device(
            device_id=device_id,
            name=name,
            ip=ip,
            trusted=False,
            public_key=public_key,
            paired_at=datetime.utcnow().isoformat(),
        )
