from __future__ import annotations
import json
import socket
import threading
import time
from pathlib import Path
from typing import Callable

import httpx

from .config import UDP_BROADCAST_PORT, HTTP_PORT
from .auth import IdentityManager


class DeviceDiscovery:
    def __init__(self, identity: IdentityManager, on_device_found: Callable[[dict[str, str]], None]) -> None:
        self.identity = identity
        self.on_device_found = on_device_found
        self.running = False
        self.thread: threading.Thread | None = None

    def _broadcast_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = json.dumps({
            "device_id": self.identity.device_id(),
            "name": socket.gethostname(),
            "port": UDP_BROADCAST_PORT,
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
        sock.bind(("", UDP_BROADCAST_PORT))
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                payload = json.loads(data.decode("utf-8"))
                if payload.get("device_id") != self.identity.device_id():
                    self.on_device_found({
                        "device_id": payload.get("device_id", ""),
                        "name": payload.get("name", "Unknown"),
                        "ip": addr[0],
                    })
            except Exception:
                continue

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self.thread.start()
        listener = threading.Thread(target=self._listen_loop, daemon=True)
        listener.start()

    def stop(self) -> None:
        self.running = False


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
