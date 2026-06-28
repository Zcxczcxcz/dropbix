# LocalHub

LocalHub is a local-first collaborative workspace for two computers on the same LAN or Wi-Fi.
It requires no cloud, no internet, and no external server. The system is built with Python, FastAPI, SQLite, WebSockets, and PySide6.

## Architecture

- `backend/` — application services, API, synchronization, storage, versioning, archive, authentication, and networking.
- `ui/` — desktop interface built with PySide6.
- `data/` — local application state and workspace storage.

## Features

- Master and Client roles.
- Pending change proposals from Clients.
- Version history with immutable snapshots.
- Local archive and trash.
- LAN discovery, PIN pairing, trusted devices.
- File preview for common formats.
- Notifications, Favorites, Timeline, and search.
- Minimal modern Russian interface.

## Running

Install dependencies:

```powershell
python -m pip install -e .
```

Start LocalHub:

```powershell
python main.py
```

Or use the bundled launcher:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_localhub.ps1
```
