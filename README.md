# LocalHub

LocalHub is a local-first collaborative workspace for two computers on the same LAN or Wi-Fi.
It requires no cloud, no internet, and no external server. The system is built with Python, FastAPI, SQLite, WebSockets, and PySide6.

## What this project does

LocalHub is a desktop application for local file sharing and collaboration between devices on the same network.
It allows you to:

- share files locally,
- track version history,
- manage pending change proposals,
- restore deleted files from trash,
- review archive events,
- work without internet and without a cloud service.

## Project structure

- `localhub/backend/` — application services, API, storage, versioning, archive, auth, and networking.
- `localhub/ui/` — desktop interface built with PySide6.
- `tests/` — basic regression tests.

## Main features

- Master and Client roles.
- Pending change proposals from Clients.
- Version history with immutable snapshots.
- Local archive and trash.
- Trusted devices and local pairing flow.
- Minimal modern Russian interface.

## Requirements

Before installing, make sure you have:

- Python 3.11+
- Git
- Internet access for installing Python packages

## Windows installation

Open PowerShell in the project folder:

```powershell
cd C:\Users\one\Desktop\dropbox\localhub
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks scripts, run this first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Upgrade pip and install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

If you prefer to install packages manually, use:

```powershell
python -m pip install fastapi "uvicorn[standard]" PySide6 httpx python-multipart watchdog cryptography
```

## Run the project

Start the app:

```powershell
python main.py
```

You can also use the bundled launcher:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_localhub.ps1
```

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## Basic Git workflow

Check status:

```powershell
git status
```

Add changes:

```powershell
git add .
```

Create a commit:

```powershell
git commit -m "Describe your changes"
```

Push to GitHub:

```powershell
git push origin main
```

Pull latest updates:

```powershell
git pull origin main
```

## Notes

This project is still a working prototype. It is suitable for local testing and learning, but it should be hardened further before being used as a production-grade secure collaboration tool.

