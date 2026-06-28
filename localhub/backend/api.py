from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .auth import IdentityManager
from .config import ensure_directories, WORKSPACE_DIR
from .db import Database
from .storage import StorageManager
from .versioning import VersionManager
from .proposals import ProposalManager
from .archive import ArchiveManager
from .settings import LocalHubSettings
from .notifications import NotificationManager
from .sync import SyncManager
from .device_manager import DeviceManager

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

clients: list[WebSocket] = []


@app.on_event("startup")
def on_startup() -> None:
    storage.ensure_workspace()


@app.get("/status")
def status() -> dict[str, Any]:
    return {
        "app": "LocalHub",
        "role": settings.role,
        "device_id": identity.device_id(),
        "trusted_devices": settings.trusted_devices,
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
    return {"archive": archive_manager.list_archive_files()}


@app.post("/sync/manual")
def sync_manual() -> dict[str, str]:
    sync_manager.manual_sync()
    return {"status": "sync_started"}


@app.get("/devices")
def devices() -> dict[str, Any]:
    return {"devices": device_manager.list_devices()}


@app.post("/devices/trust")
def trust_device(device_id: str) -> dict[str, Any]:
    device_manager.trust_device(device_id)
    archive_manager.archive_event("device_trusted", f"Устройство доверено: {device_id}", details=device_id)
    return {"status": "trusted", "device_id": device_id}


@app.post("/devices/untrust")
def untrust_device(device_id: str) -> dict[str, Any]:
    device_manager.untrust_device(device_id)
    archive_manager.archive_event("device_untrusted", f"Устройство больше не доверено: {device_id}", details=device_id)
    return {"status": "untrusted", "device_id": device_id}


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
