# Building

## Prerequisites

**Python** ≥ 3.10
**Node.js** ≥ 24, **npm** ≥ 9

### First-time setup

```bash
# Install Python dependencies (server extra required for the web app)
pip install -e ".[server]"

# Install frontend dependencies
npm install

# For running tests
pip install -e ".[server,dev]"

# For building desktop executables
pip install -e ".[server,desktop]"
```

Using a virtual environment is recommended:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[server,dev,desktop]"
```

---

## Development

All `npm run …` commands below are run from the **repository root** (they live in the root `package.json`, not `frontend/`).

Two servers run in development: the Vite frontend dev server and the Python backend. Vite proxies all API and WebSocket requests to the backend, so you only open the Vite URL in your browser.

The easiest way is the combined runner, which starts both processes in the same terminal with interleaved output and tears everything down on Ctrl-C:

```bash
npm run dev:all
```

Or run them in separate terminals if you prefer independent logs:

```bash
# Terminal 1 — Python backend (http://127.0.0.1:8188)
npm run backend

# Terminal 2 — Vite frontend with hot-reload
npm run dev
```

Open the URL printed by Vite (typically `http://localhost:5173`).

Changes to Python files take effect after restarting the backend. Changes to frontend files hot-reload automatically.

---

## Web deployment

Build the frontend bundle and serve the backend:

```bash
# Build frontend to frontend/dist/
npm run build

# Start the server (serves the built frontend at /)
python -m backend.main
```

The server listens on `http://127.0.0.1:8188` by default. It serves the built frontend from `frontend/dist/` and exposes the REST + WebSocket API.

The web mode is a multi-session server: each browser tab gets its own session and isolated file workspace. Local filesystem access is disabled (users upload files through the browser).

---

## Desktop app

The desktop app uses pywebview to embed the frontend in a native window. The Python server runs in a background thread; the app picks a free port automatically.

```bash
# Build frontend + launch desktop app
npm run desktop
```

This is equivalent to `npm run build && python desktop.py`.

In desktop mode `allow_local_filesystem=True`, which means:
- Users can open files directly from their filesystem
- The plugin system is enabled (see [plugins.md](plugins.md))

---

## Building desktop executables

The build scripts use PyInstaller to produce a self-contained executable. They build the frontend first, then package everything (Python runtime, backend, `frontend/dist/`, `demo/`) into a single distributable.

### macOS

Produces a `.app` bundle and a `.dmg` installer.

```bash
npm run build:mac
# Output: desktop-dist/tono.dmg
```

Options:
```bash
bash scripts/build-mac.sh --onefile   # Single executable instead of bundle
bash scripts/build-mac.sh --no-dmg    # Skip DMG creation
```

### Linux

Produces a `.tar.gz` archive containing the app directory.

```bash
npm run build:linux
# Output: desktop-dist/tono-linux.tar.gz
```

Options:
```bash
bash scripts/build-linux.sh --onefile  # Single executable
bash scripts/build-linux.sh --no-tar   # Skip archive creation
```

### Windows

Produces a `tono.exe` inside an output folder.

```powershell
npm run build:windows
# Output: desktop-dist\tono\tono.exe
```

Options:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1 -OneFile
```

> **Note:** Run the build scripts from the repo root. They expect a `.venv` at the repo root; if not found, they fall back to the system `python` / `python3`.

---

## Runtime data directories

| Mode | Directory |
|---|---|
| Development | Repo root (`input/`, `output/`, `plugins/`) |
| macOS packaged | `~/Library/Application Support/tono/` |
| Linux packaged | `~/.local/share/tono/` |
| Windows packaged | `%LOCALAPPDATA%\tono\` |

Override with the `TONO_APPDATA` environment variable:

```bash
TONO_APPDATA=/my/data/dir python desktop.py
```

---

## Key npm scripts summary

| Command | Description |
|---|---|
| `npm run dev:all` | Start the Python backend and the Vite dev server together |
| `npm run dev` | Start the Vite dev server only |
| `npm run backend` | Start the Python backend only |
| `npm run build` | Build frontend to `frontend/dist/` |
| `npm run preview` | Preview the production frontend build |
| `npm run desktop` | Build frontend + launch desktop app |
| `npm run build:mac` | Build macOS `.dmg` |
| `npm run build:linux` | Build Linux `.tar.gz` |
| `npm run build:windows` | Build Windows `.exe` |
