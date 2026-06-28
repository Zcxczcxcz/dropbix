from __future__ import annotations
import json
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

from .config import IDENTITY_PATH, DEVICES_PATH
from .db import Database


def _read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


class IdentityManager:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.private_key = self._load_or_create_private_key()
        self.public_key = self.private_key.public_key()

    def _load_or_create_private_key(self) -> Ed25519PrivateKey:
        if IDENTITY_PATH.exists():
            data = IDENTITY_PATH.read_bytes()
            return serialization.load_pem_private_key(data, password=None)
        private_key = Ed25519PrivateKey.generate()
        pem_data = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        IDENTITY_PATH.write_bytes(pem_data)
        return private_key

    def device_id(self) -> str:
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return public_bytes.hex()

    def public_key_pem(self) -> str:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def sign_message(self, message: bytes) -> bytes:
        return self.private_key.sign(message)

    def verify_remote_signature(self, remote_public_pem: str, message: bytes, signature: bytes) -> bool:
        public_key = serialization.load_pem_public_key(remote_public_pem.encode("utf-8"))
        if not isinstance(public_key, Ed25519PublicKey):
            return False
        try:
            public_key.verify(signature, message)
            return True
        except Exception:
            return False

    def pair_device(self, name: str, ip: str, public_key_pem: str, accepted: bool) -> None:
        device_id = self._device_id_from_public_key(public_key_pem)
        timestamp = datetime.utcnow().isoformat()
        self.db.insert_device(
            device_id=device_id,
            name=name,
            ip=ip,
            trusted=accepted,
            public_key=public_key_pem,
            paired_at=timestamp,
        )

    def _device_id_from_public_key(self, public_key_pem: str) -> str:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        raw = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return raw.hex()

    def get_trusted_devices(self) -> list[str]:
        rows = self.db.fetchall("SELECT device_id FROM devices WHERE trusted = 1")
        return [row["device_id"] for row in rows]

    def create_pairing_pin(self) -> str:
        return secrets.token_hex(2)

    def register_device(self, device_id: str, name: str, ip: str, trusted: bool) -> None:
        self.db.insert_device(device_id=device_id, name=name, ip=ip, trusted=trusted, public_key=None, paired_at=datetime.utcnow().isoformat())
