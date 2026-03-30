# tono

tono is a node-based image analysis application with:

- a Python backend built on `aiohttp`
- a React + Vite frontend
- an optional desktop wrapper built with `pywebview`

The backend serves node definitions, runs workflows, manages file I/O, and streams previews/results over WebSocket. The frontend provides the graph editor and UI. The desktop build packages both together as a Windows application.

## Project Layout

```text
tono/
  backend/         Python server, execution engine, nodes
  frontend/        React/Vite app
  tests/           Python tests
  desktop.py       Local desktop launcher
  scripts/         Build helpers, including Windows exe packaging
```

## Requirements

- Python `3.10+`
- Node.js `18+`
- npm `9+`
- Windows is recommended for the desktop `.exe` packaging flow

## First-Time Setup

Create a virtual environment if you do not already have one:

```powershell
python -m venv .venv
```

Install Python dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Install Node dependencies from the repo root:

```powershell
npm install
```

Optional extras:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[dev]
.\.venv\Scripts\python.exe -m pip install -e .[spm]
.\.venv\Scripts\python.exe -m pip install -e .[desktop]
```

- `dev`: test tooling
- `spm`: optional SPM/AFM file readers like `gwyfile`, `nanonispy`, and `igor`
- `desktop`: desktop launcher and PyInstaller packaging tools

## Running the Local Web Version

This is the normal browser-based development flow.

In terminal 1, start the backend:

```powershell
npm run backend
```

This starts the Python server at `http://127.0.0.1:8188`.

In terminal 2, start the Vite frontend:

```powershell
npm run dev
```

Open the Vite URL shown in the terminal, typically:

```text
http://127.0.0.1:5173
```

Notes:

- The frontend dev server proxies API and WebSocket requests to the backend.
- `npm run dev` now clears Vite's local cache and stale Python bytecode first, then starts Vite with `--force`.
- If you open the backend directly in a browser instead of the Vite dev server, tono now refreshes `frontend/dist` automatically when checked-out frontend sources are newer, such as after a `git pull`.
- If you want the frontend accessible from other devices on your LAN, run:

```powershell
npm run dev -- --host 0.0.0.0
```

## Running the Local Desktop Version

The desktop launcher starts the Python server internally and opens a native window with `pywebview`.
`npm run desktop` now rebuilds the frontend first so the native app always uses a fresh `frontend/dist`.

Launch the desktop app from source:

```powershell
npm run desktop
```

Notes:

- `npm run build` clears stale frontend output, Vite cache, and Python bytecode before producing `frontend/dist`.

## Building the Windows `.exe`

The repo includes a packaging script that:

1. builds the frontend
2. installs desktop build dependencies
3. runs PyInstaller

Build the desktop bundle:

```powershell
npm run build:desktop
```

Or run the script directly:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-desktop.ps1
```

The packaged app is written to:

```text
desktop-dist/tono/
```

Main executable:

```text
desktop-dist/tono/tono.exe
```

### One-File Build

The default build uses PyInstaller `--onedir`, which is more reliable for scientific Python packages like NumPy, SciPy, and Matplotlib.

If you still want to try a single-file executable:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-desktop.ps1 -OneFile
```

## Data Directories

During normal source-based development, input/output folders live under the repo root.

In the packaged desktop app, writable data is stored under:

```text
%LOCALAPPDATA%\tono\
```

Specifically:

```text
%LOCALAPPDATA%\tono\input
%LOCALAPPDATA%\tono\output
```

You can override the packaged app data directory with:

```powershell
$env:TONO_APPDATA="C:\path\to\custom\data"
```

## Useful Commands

```powershell
npm run dev
npm run build
npm run preview
npm run backend
npm run desktop
npm run build:desktop
.\.venv\Scripts\python.exe -m pytest -q
```

## Testing

Run the Python test suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Known Notes

- The frontend production build currently emits a large chunk warning from Vite. This does not block builds.
- The desktop app relies on WebView2 on Windows through `pywebview`.
- Optional SPM readers are not installed unless you explicitly install the `spm` extra.
