from __future__ import annotations
import json
import socket
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .auth import IdentityManager
from .config import ensure_directories, WORKSPACE_DIR, HTTP_PORT
from .db import Database
from .storage import StorageManager
from .versioning import VersionManager
from .proposals import ProposalManager
from .archive import ArchiveManager
from .settings import LocalHubSettings
from .notifications import NotificationManager
from .sync import SyncManager
from .device_manager import DeviceManager
from .network import DeviceDiscovery

app = FastAPI(title="LocalHub API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_directories()
db = Database()
settings = LocalHubSettings.load()
storage = StorageManager(db=db)
version_manager = VersionManager(db=db, storage=storage)
proposal_manager = ProposalManager(db=db, storage=storage)
archive_manager = ArchiveManager(db=db)
notifications = NotificationManager(db=db)
sync_manager = SyncManager(db=db, storage=storage, version_manager=version_manager)
identity = IdentityManager(db=db)
device_manager = DeviceManager(db=db, identity=identity)

discovery = DeviceDiscovery(
    identity=identity,
    on_device_found=device_manager.register_discovered_device,
)

clients: list[WebSocket] = []


def _device_display_name() -> str:
    return settings.device_name or socket.gethostname()


@app.on_event("startup")
def on_startup() -> None:
    storage.ensure_workspace()
    discovery.set_device_name(_device_display_name())
    discovery.start()
    if settings.auto_sync:
        sync_manager.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    discovery.stop()
    sync_manager.stop()


@app.get("/status")
def status() -> dict[str, Any]:
    return {
        "app": "LocalHub",
        "role": settings.role,
        "device_id": identity.device_id(),
        "device_name": _device_display_name(),
        "hostname": socket.gethostname(),
        "public_key": identity.public_key_pem(),
        "http_port": HTTP_PORT,
        "trusted_devices": device_manager.get_trusted_device_ids(),
        "scanning": discovery.scanning,
    }


@app.get("/files")
def list_files() -> dict[str, Any]:
    files = storage.list_shared_files()
    return {"files": files}


@app.get("/file")
def get_file(path: str) -> FileResponse:
    file_path = storage.workspace_path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(file_path)


@app.post("/file/upload")
def upload_file(path: str = Form(...), comment: str = Form(""), file: UploadFile = File(...)) -> dict[str, Any]:
    if settings.role != "master":
        data = file.file.read()
        proposal_id = proposal_manager.create_proposal(file_path=path, sender_device=identity.device_id(), action="upload", payload=data, comment=comment)
        archive_manager.archive_event("proposal_created", f"Пользователь предложил изменение {path}", details=f"proposal_id={proposal_id}")
        return {"status": "pending", "proposal_id": proposal_id}
    dest_path = storage.workspace_path(path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(file.file.read())
    version_manager.create_version(path, author=identity.device_id(), comment=comment)
    archive_manager.archive_event("file_uploaded", f"Файл {path} добавлен", details=path)
    return {"status": "saved", "path": path}


@app.get("/pending")
def pending_changes() -> dict[str, Any]:
    return {"pending": proposal_manager.list_pending()}


@app.post("/proposal/accept")
def accept_proposal(proposal_id: int) -> dict[str, Any]:
    if settings.role != "master":
        raise HTTPException(status_code=403, detail="Только мастер может принимать изменения")
    proposal = proposal_manager.apply_proposal(proposal_id)
    version_manager.create_version(proposal["file_path"], author=proposal["sender_device"], comment=proposal["comment"])
    archive_manager.archive_event("proposal_accepted", f"Изменение принято для {proposal['file_path']}", details=f"proposal_id={proposal_id}")
    return {"status": "accepted", "proposal_id": proposal_id}


@app.post("/proposal/reject")
def reject_proposal(proposal_id: int) -> dict[str, Any]:
    if settings.role != "master":
        raise HTTPException(status_code=403, detail="Только мастер может отклонять изменения")
    proposal_manager.reject_proposal(proposal_id)
    archive_manager.archive_event("proposal_rejected", f"Изменение отклонено для proposal {proposal_id}", details=f"proposal_id={proposal_id}")
    return {"status": "rejected", "proposal_id": proposal_id}


@app.get("/history")
def history() -> dict[str, Any]:
    return {"history": version_manager.get_history()}


@app.post("/version/restore")
def restore_version(version_id: int) -> dict[str, Any]:
    version = version_manager.restore_version(version_id)
    archive_manager.archive_event("version_restored", f"Версия восстановлена: {version['file_path']}", details=f"version_id={version_id}")
    return {"status": "restored", "version": version}


@app.delete("/file")
def delete_file(path: str) -> dict[str, Any]:
    result = storage.move_to_trash(path)
    if result is None:
        raise HTTPException(status_code=404, detail="Файл не найден")
    db.set_file_deleted(path, True)
    if path in settings.favorites:
        settings.remove_favorite(path)
    archive_manager.archive_event("file_deleted", f"Файл перемещён в корзину: {path}", details=path)
    return {"status": "moved_to_trash", "path": path}


@app.get("/trash")
def trash() -> dict[str, Any]:
    return {"trash": storage.list_trash()}


@app.post("/trash/restore")
def restore_trash(path: str) -> dict[str, Any]:
    restored = storage.restore_from_trash(path)
    if restored is None:
        raise HTTPException(status_code=404, detail="Файл не найден в корзине")
    db.set_file_deleted(path, False)
    archive_manager.archive_event("trash_restored", f"Файл восстановлен из корзины: {path}", details=path)
    return {"status": "restored", "path": path}


@app.post("/proposal/receive")
def receive_proposal(path: str = Form(...), comment: str = Form(""), sender_device: str = Form(...), file: UploadFile = File(...)) -> dict[str, Any]:
    data = file.file.read()
    proposal_id = proposal_manager.create_proposal(file_path=path, sender_device=sender_device, action="upload", payload=data, comment=comment)
    archive_manager.archive_event("proposal_received", f"Принято предложение {path} от {sender_device}", details=f"proposal_id={proposal_id}")
    return {"status": "pending", "proposal_id": proposal_id}


@app.get("/archive")
def archive() -> dict[str, Any]:
    events = archive_manager.list_events()
    formatted = [
        f"[{event['timestamp']}] {event['event_type']}: {event['description']}"
        for event in events
    ]
    return {"archive": formatted, "events": events}


@app.post("/sync/manual")
def sync_manual() -> dict[str, str]:
    sync_manager.manual_sync()
    settings.last_sync = __import__("datetime").datetime.utcnow().isoformat()
    settings.save()
    return {"status": "sync_started"}


@app.get("/devices")
def devices() -> dict[str, Any]:
    return {"devices": device_manager.list_devices()}


@app.post("/devices/scan")
def scan_devices() -> dict[str, Any]:
    discovery.trigger_scan()
    return {"status": "scanning", "scanning": True}


@app.get("/devices/scan/status")
def scan_status() -> dict[str, Any]:
    return {
        "scanning": discovery.scanning,
        "last_scan_at": discovery.last_scan_at,
    }


@app.post("/devices/add")
def add_device(ip: str, name: str = "") -> dict[str, Any]:
    try:
        info = device_manager.add_device_by_ip(ip=ip, name=name or None)
        archive_manager.archive_event("device_added", f"Устройство добавлено: {info.get('name', ip)}", details=ip)
        return {"status": "added", "device": info}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/devices/{device_id}")
def remove_device(device_id: str) -> dict[str, Any]:
    try:
        device_manager.remove_device(device_id)
        archive_manager.archive_event("device_removed", f"Устройство удалено: {device_id}", details=device_id)
        return {"status": "removed", "device_id": device_id}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/devices/trust")
def trust_device(device_id: str) -> dict[str, Any]:
    try:
        device_manager.trust_device(device_id)
        archive_manager.archive_event("device_trusted", f"Устройство доверено: {device_id}", details=device_id)
        return {"status": "trusted", "device_id": device_id}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/devices/untrust")
def untrust_device(device_id: str) -> dict[str, Any]:
    try:
        device_manager.untrust_device(device_id)
        archive_manager.archive_event("device_untrusted", f"Устройство больше не доверено: {device_id}", details=device_id)
        return {"status": "untrusted", "device_id": device_id}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/settings")
def get_settings() -> dict[str, Any]:
    return {
        "role": settings.role,
        "auto_sync": settings.auto_sync,
        "language": settings.language,
        "device_name": settings.device_name,
        "favorites": settings.favorites,
        "last_sync": settings.last_sync,
        "device_id": identity.device_id(),
    }


@app.post("/settings")
def update_settings(
    role: str | None = None,
    auto_sync: bool | None = None,
    device_name: str | None = None,
) -> dict[str, Any]:
    if role is not None and role in ("master", "client"):
        settings.role = role
    if auto_sync is not None:
        settings.auto_sync = auto_sync
        if auto_sync:
            sync_manager.start()
        else:
            sync_manager.stop()
    if device_name is not None:
        settings.device_name = device_name.strip()
        discovery.set_device_name(settings.device_name or socket.gethostname())
    settings.save()
    return get_settings()


@app.get("/favorites")
def get_favorites() -> dict[str, Any]:
    return {"favorites": settings.favorites}


@app.post("/favorites/add")
def add_favorite(path: str) -> dict[str, Any]:
    storage.ensure_workspace()
    db.ensure_file_record(path, created_at=__import__("datetime").datetime.utcnow().isoformat())
    settings.add_favorite(path)
    db.set_favorite(path, True)
    return {"status": "added", "path": path}


@app.post("/favorites/remove")
def remove_favorite(path: str) -> dict[str, Any]:
    settings.remove_favorite(path)
    db.set_favorite(path, False)
    return {"status": "removed", "path": path}


@app.get("/notifications")
def get_notifications() -> dict[str, list[dict[str, str | None]]]:
    return {"notifications": notifications.latest()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            for client in clients:
                if client is not websocket:
                    await client.send_text(json.dumps(payload))
    except WebSocketDisconnect:
        clients.remove(websocket)
