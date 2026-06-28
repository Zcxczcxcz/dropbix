from __future__ import annotations
from datetime import datetime
from pathlib import Path
import uuid

from .db import Database
from .storage import StorageManager


class ProposalManager:
    def __init__(self, db: Database, storage: StorageManager) -> None:
        self.db = db
        self.storage = storage

    def create_proposal(self, file_path: str, sender_device: str, action: str, payload: bytes, comment: str | None = "") -> int:
        proposal_id = uuid.uuid4().hex
        payload_file = self.storage.proposal_path(proposal_id)
        payload_file.write_bytes(payload)
        timestamp = datetime.utcnow().isoformat()
        return self.db.insert_proposal(
            file_path=file_path,
            sender_device=sender_device,
            timestamp=timestamp,
            status="pending",
            comment=comment or "",
            action=action,
            payload_path=str(payload_file),
        )

    def list_pending(self) -> list[dict[str, str | int]]:
        rows = self.db.fetchall(
            "SELECT * FROM proposals WHERE status = 'pending' ORDER BY timestamp DESC",
        )
        return [dict(row) for row in rows]

    def update_proposal_status(self, proposal_id: int, new_status: str) -> None:
        self.db.execute(
            "UPDATE proposals SET status = ? WHERE id = ?",
            (new_status, proposal_id),
        )

    def get_proposal(self, proposal_id: int) -> dict[str, str | int] | None:
        row = self.db.fetchone("SELECT * FROM proposals WHERE id = ?", (proposal_id,))
        return dict(row) if row else None

    def apply_proposal(self, proposal_id: int) -> dict[str, str | int]:
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            raise ValueError("Proposal not found")
        payload_path = Path(proposal["payload_path"])
        target_path = self.storage.workspace_path(proposal["file_path"])
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(payload_path.read_bytes())
        self.update_proposal_status(proposal_id, "accepted")
        return proposal

    def reject_proposal(self, proposal_id: int) -> None:
        self.update_proposal_status(proposal_id, "rejected")
