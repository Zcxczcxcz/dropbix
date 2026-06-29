from __future__ import annotations
import json
from pathlib import Path
from typing import Any

import httpx


class ApiClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8743") -> None:
        self.base_url = base_url
        self.client = httpx.Client(base_url=self.base_url, timeout=10.0)

    def _request(self, method: str, url: str, default: Any = None, **kwargs: Any) -> Any:
        try:
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
        except Exception:
            return default if default is not None else {}

    def status(self) -> dict[str, Any]:
        return self._request("GET", "/status", default={})

    def list_files(self) -> list[str]:
        return self._request("GET", "/files", default={"files": []})["files"]

    def get_file(self, path: str, destination: Path) -> Path:
        try:
            response = self.client.get("/file", params={"path": path})
            response.raise_for_status()
            destination.write_bytes(response.content)
        except Exception:
            destination.write_bytes(b"")
        return destination

    def upload_file(self, path: str, data: bytes, comment: str = "") -> dict[str, Any]:
        files = {"file": (Path(path).name, data)}
        payload = {"path": path, "comment": comment}
        return self._request("POST", "/file/upload", default={"status": "error"}, data=payload, files=files)

    def list_pending(self) -> list[dict[str, Any]]:
        return self._request("GET", "/pending", default={"pending": []})["pending"]

    def accept_proposal(self, proposal_id: int) -> dict[str, Any]:
        return self._request("POST", "/proposal/accept", default={"status": "error"}, params={"proposal_id": proposal_id})

    def reject_proposal(self, proposal_id: int) -> dict[str, Any]:
        return self._request("POST", "/proposal/reject", default={"status": "error"}, params={"proposal_id": proposal_id})

    def history(self) -> list[dict[str, Any]]:
        return self._request("GET", "/history", default={"history": []})["history"]

    def restore_version(self, version_id: int) -> dict[str, Any]:
        return self._request("POST", "/version/restore", default={"status": "error"}, params={"version_id": version_id})

    def list_trash(self) -> list[str]:
        return self._request("GET", "/trash", default={"trash": []})["trash"]

    def restore_trash(self, path: str) -> dict[str, Any]:
        return self._request("POST", "/trash/restore", default={"status": "error"}, params={"path": path})

    def delete_file(self, path: str) -> dict[str, Any]:
        return self._request("DELETE", "/file", default={"status": "error"}, params={"path": path})

    def list_archive(self) -> list[str]:
        return self._request("GET", "/archive", default={"archive": []})["archive"]

    def list_notifications(self) -> list[dict[str, str | None]]:
        return self._request("GET", "/notifications", default={"notifications": []})["notifications"]

    def list_devices(self) -> list[dict[str, Any]]:
        return self._request("GET", "/devices", default={"devices": []})["devices"]

    def scan_devices(self) -> dict[str, Any]:
        return self._request("POST", "/devices/scan", default={"status": "error"})

    def scan_status(self) -> dict[str, Any]:
        return self._request("GET", "/devices/scan/status", default={"scanning": False})

    def add_device(self, ip: str, name: str = "") -> dict[str, Any]:
        return self._request("POST", "/devices/add", default={"status": "error"}, params={"ip": ip, "name": name})

    def remove_device(self, device_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/devices/{device_id}", default={"status": "error"})

    def trust_device(self, device_id: str) -> dict[str, Any]:
        return self._request("POST", "/devices/trust", default={"status": "error"}, params={"device_id": device_id})

    def untrust_device(self, device_id: str) -> dict[str, Any]:
        return self._request("POST", "/devices/untrust", default={"status": "error"}, params={"device_id": device_id})

    def get_settings(self) -> dict[str, Any]:
        return self._request("GET", "/settings", default={})

    def update_settings(self, role: str | None = None, auto_sync: bool | None = None, device_name: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if role is not None:
            params["role"] = role
        if auto_sync is not None:
            params["auto_sync"] = auto_sync
        if device_name is not None:
            params["device_name"] = device_name
        return self._request("POST", "/settings", default={}, params=params)

    def list_favorites(self) -> list[str]:
        return self._request("GET", "/favorites", default={"favorites": []})["favorites"]

    def add_favorite(self, path: str) -> dict[str, Any]:
        return self._request("POST", "/favorites/add", default={"status": "error"}, params={"path": path})

    def remove_favorite(self, path: str) -> dict[str, Any]:
        return self._request("POST", "/favorites/remove", default={"status": "error"}, params={"path": path})

    def manual_sync(self) -> dict[str, Any]:
        return self._request("POST", "/sync/manual", default={"status": "error"})
