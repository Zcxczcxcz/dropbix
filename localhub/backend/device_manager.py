from __future__ import annotations
from datetime import datetime
from typing import Any
import socket

from .auth import IdentityManager
from .config import HTTP_PORT
from .db import Database
from .network import probe_device


class DeviceManager:
    def __init__(self, db: Database, identity: IdentityManager) -> None:
        self.db = db
        self.identity = identity
        self.discovered_devices: dict[str, dict[str, str]] = {}

    def register_discovered_device(self, info: dict[str, str]) -> None:
        device_id = info.get("device_id", "")
        if not device_id or device_id == self.identity.device_id():
            return
        name = info.get("name", "Unknown")
        ip = info.get("ip", "")
        public_key = info.get("public_key") or ""
        self.discovered_devices[device_id] = {
            "device_id": device_id,
            "name": name,
            "ip": ip,
            "public_key": public_key,
            "trusted": "0",
            "role": info.get("role", ""),
        }
        existing = self.db.fetchone("SELECT device_id FROM devices WHERE device_id = ?", (device_id,))
        if not existing:
            self.db.insert_device(
                device_id=device_id,
                name=name,
                ip=ip,
                trusted=False,
                public_key=public_key or None,
                paired_at=datetime.utcnow().isoformat(),
            )
        else:
            self.db.execute(
                "UPDATE devices SET name = ?, ip = ? WHERE device_id = ?",
                (name, ip, device_id),
            )

    def list_devices(self) -> list[dict[str, Any]]:
        rows = self.db.fetchall("SELECT device_id, name, ip, trusted, public_key, paired_at FROM devices")
        devices: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            device_id = row["device_id"]
            if device_id == self.identity.device_id():
                continue
            seen.add(device_id)
            devices.append(self._format_device(dict(row)))
        for device_id, info in self.discovered_devices.items():
            if device_id not in seen and device_id != self.identity.device_id():
                devices.append({
                    "device_id": info["device_id"],
                    "name": info["name"],
                    "ip": info["ip"],
                    "trusted": False,
                    "public_key": info.get("public_key", ""),
                    "paired_at": None,
                    "online": self._is_online(info.get("ip", "")),
                    "role": info.get("role", ""),
                })
        return devices

    def _format_device(self, row: dict[str, Any]) -> dict[str, Any]:
        ip = row.get("ip") or ""
        return {
            "device_id": row["device_id"],
            "name": row["name"],
            "ip": ip,
            "trusted": bool(row.get("trusted")),
            "public_key": row.get("public_key") or "",
            "paired_at": row.get("paired_at"),
            "online": self._is_online(ip),
            "role": "",
        }

    def _is_online(self, ip: str) -> bool:
        if not ip:
            return False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.35)
            result = sock.connect_ex((ip, HTTP_PORT))
            sock.close()
            return result == 0
        except OSError:
            return False

    def trust_device(self, device_id: str) -> None:
        row = self.db.fetchone("SELECT device_id, name, ip, public_key FROM devices WHERE device_id = ?", (device_id,))
        if not row:
            raise ValueError("Устройство не найдено")
        self.db.insert_device(
            device_id=row["device_id"],
            name=row["name"],
            ip=row["ip"],
            trusted=True,
            public_key=row["public_key"],
            paired_at=datetime.utcnow().isoformat(),
        )

    def untrust_device(self, device_id: str) -> None:
        row = self.db.fetchone("SELECT device_id, name, ip, public_key, paired_at FROM devices WHERE device_id = ?", (device_id,))
        if not row:
            raise ValueError("Устройство не найдено")
        self.db.insert_device(
            device_id=row["device_id"],
            name=row["name"],
            ip=row["ip"],
            trusted=False,
            public_key=row["public_key"],
            paired_at=row["paired_at"],
        )

    def remove_device(self, device_id: str) -> None:
        if device_id == self.identity.device_id():
            raise ValueError("Нельзя удалить собственное устройство")
        self.discovered_devices.pop(device_id, None)
        self.db.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))

    def get_trusted_device_ids(self) -> list[str]:
        rows = self.db.fetchall("SELECT device_id FROM devices WHERE trusted = 1")
        return [row["device_id"] for row in rows]

    def add_device_by_ip(self, ip: str, name: str | None = None) -> dict[str, str]:
        info = probe_device(ip.strip())
        if info:
            if info.get("device_id") == self.identity.device_id():
                raise ValueError("Нельзя добавить собственное устройство")
            if name:
                info["name"] = name
            self.register_discovered_device(info)
            return info
        device_id = f"manual-{ip.replace('.', '-')}"
        display_name = name or f"Устройство {ip}"
        self.manual_connect(device_id, display_name, ip)
        return {"device_id": device_id, "name": display_name, "ip": ip}

    def manual_connect(self, device_id: str, name: str, ip: str, public_key: str | None = None) -> None:
        if device_id == self.identity.device_id():
            return
        self.discovered_devices[device_id] = {
            "device_id": device_id,
            "name": name,
            "ip": ip,
            "public_key": public_key or "",
            "trusted": "0",
            "role": "",
        }
        self.db.insert_device(
            device_id=device_id,
            name=name,
            ip=ip,
            trusted=False,
            public_key=public_key,
            paired_at=datetime.utcnow().isoformat(),
        )
