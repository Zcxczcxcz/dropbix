from __future__ import annotations
from dataclasses import dataclass


@dataclass
class FileInfo:
    path: str
    deleted: bool
    favorite: bool
    created_at: str


@dataclass
class VersionInfo:
    id: int
    file_path: str
    version: int
    timestamp: str
    author: str
    checksum: str
    comment: str
    content_path: str


@dataclass
class ProposalInfo:
    id: int
    file_path: str
    sender_device: str
    timestamp: str
    status: str
    comment: str
    action: str
    payload_path: str


@dataclass
class DeviceInfo:
    device_id: str
    name: str
    ip: str
    trusted: bool
    public_key: str | None
    paired_at: str | None


@dataclass
class EventRecord:
    id: int
    event_type: str
    description: str
    timestamp: str
    device_id: str | None
    details: str | None
