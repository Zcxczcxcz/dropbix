from __future__ import annotations
import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import httpx

from .config import UDP_BROADCAST_PORT, HTTP_PORT
from .auth import IdentityManager


def _local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


def _subnet_hosts(ip: str) -> list[str]:
    parts = ip.split(".")
    if len(parts) != 4:
        return []
    base = ".".join(parts[:3])
    return [f"{base}.{host}" for host in range(1, 255)]


def probe_device(ip: str, port: int = HTTP_PORT, timeout: float = 1.5) -> dict[str, str] | None:
    url = f"http://{ip}:{port}/status"
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
            if payload.get("app") != "LocalHub":
                return None
            return {
                "device_id": payload.get("device_id", ""),
                "name": payload.get("device_name") or payload.get("hostname", "Unknown"),
                "ip": ip,
                "role": payload.get("role", ""),
                "public_key": payload.get("public_key", ""),
            }
    except Exception:
        return None


class DeviceDiscovery:
    def __init__(self, identity: IdentityManager, on_device_found: Callable[[dict[str, str]], None]) -> None:
        self.identity = identity
        self.on_device_found = on_device_found
        self.running = False
        self.scanning = False
        self.last_scan_at: str | None = None
        self._broadcast_thread: threading.Thread | None = None
        self._listen_thread: threading.Thread | None = None
        self._scan_thread: threading.Thread | None = None
        self._device_name = socket.gethostname()

    def set_device_name(self, name: str) -> None:
        self._device_name = name or socket.gethostname()

    def _broadcast_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = json.dumps({
            "device_id": self.identity.device_id(),
            "name": self._device_name,
            "hostname": socket.gethostname(),
            "http_port": HTTP_PORT,
        }).encode("utf-8")
        while self.running:
            try:
                sock.sendto(message, ("<broadcast>", UDP_BROADCAST_PORT))
            except OSError:
                pass
            time.sleep(5)

    def _listen_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", UDP_BROADCAST_PORT))
        except OSError:
            return
        while self.running:
            try:
                data, addr = sock.recvfrom(2048)
                payload = json.loads(data.decode("utf-8"))
                device_id = payload.get("device_id", "")
                if not device_id or device_id == self.identity.device_id():
                    continue
                info = probe_device(addr[0]) or {
                    "device_id": device_id,
                    "name": payload.get("name", "Unknown"),
                    "ip": addr[0],
                    "role": "",
                    "public_key": "",
                }
                self.on_device_found(info)
            except Exception:
                continue

    def _scan_subnet(self) -> None:
        self.scanning = True
        local_ip = _local_ip()
        hosts = _subnet_hosts(local_ip)
        own_id = self.identity.device_id()
        try:
            with ThreadPoolExecutor(max_workers=32) as executor:
                futures = {executor.submit(probe_device, host): host for host in hosts if host != local_ip}
                for future in as_completed(futures):
                    if not self.scanning:
                        break
                    try:
                        info = future.result()
                    except Exception:
                        continue
                    if info and info.get("device_id") and info["device_id"] != own_id:
                        self.on_device_found(info)
        except Exception:
            pass
        finally:
            self.scanning = False
            self.last_scan_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._broadcast_thread.start()
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()
        self.trigger_scan()

    def trigger_scan(self) -> None:
        if self.scanning:
            return
        self._scan_thread = threading.Thread(target=self._scan_subnet, daemon=True)
        self._scan_thread.start()

    def stop(self) -> None:
        self.running = False
        self.scanning = False


class LocalHubServer:
    def __init__(self, identity: IdentityManager, on_connection: Callable[[dict[str, str]], None]) -> None:
        self.identity = identity
        self.on_connection = on_connection
        self.running = False
        self.thread: threading.Thread | None = None

    def _serve(self) -> None:
        while self.running:
            time.sleep(0.5)

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False

    def send_proposal(self, device_ip: str, file_path: str, payload: bytes, comment: str, sender_device: str) -> dict[str, str | int]:
        url = f"http://{device_ip}:{HTTP_PORT}/proposal/receive"
        files = {"file": (Path(file_path).name, payload)}
        data = {"path": file_path, "comment": comment, "sender_device": sender_device}
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, data=data, files=files)
            response.raise_for_status()
            return response.json()
