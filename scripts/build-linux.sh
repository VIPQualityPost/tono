#!/usr/bin/env bash
set -euo pipefail

ONE_FILE=false
CREATE_TAR=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --onefile)  ONE_FILE=true;  shift ;;
        --no-tar)   CREATE_TAR=false; shift ;;
        *)          echo "Unknown option: $1"; exit 1 ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ -d ".venv/bin" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

FRONTEND_DIST="$REPO_ROOT/frontend/dist"
DEMO_DIR="$REPO_ROOT/demo"

echo "Building frontend bundle..."
npm run build

echo "Installing desktop build dependencies..."
uv pip install -e ".[desktop]"

if $ONE_FILE; then
    MODE="--onefile"
else
    MODE="--onedir"
fi

echo "Packaging desktop app with PyInstaller..."
$PYTHON -m PyInstaller \
    desktop.py \
    --noconfirm \
    --clean \
    --name tono \
    --windowed \
    $MODE \
    --distpath desktop-dist \
    --workpath desktop-build \
    --specpath desktop-build \
    --add-data "${FRONTEND_DIST}:frontend/dist" \
    --add-data "${DEMO_DIR}:demo" \
    --collect-all matplotlib \
    --collect-all scipy \
    --collect-all skimage \
    --collect-all webview

if $CREATE_TAR; then
    TAR_PATH="desktop-dist/tono-linux.tar.gz"
    echo "Creating tarball..."
    tar -czf "$TAR_PATH" -C desktop-dist tono
    echo "Tarball created: $TAR_PATH"
fi

echo "Desktop build complete."
echo "Output: $REPO_ROOT/desktop-dist/"
