#!/usr/bin/env bash
set -euo pipefail

CREATE_TAR=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-tar)   CREATE_TAR=false; shift ;;
        *)          echo "Unknown option: $1"; exit 1 ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

source .venv/bin/activate

if [ -d ".venv/bin" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

FRONTEND_DIST="$REPO_ROOT/frontend/dist"
DEMO_DIR="$REPO_ROOT/demo"

# Bake the git-tag-derived version (nearest tag, fallback to short hash or "dev").
# Read at runtime via resource_root()/build_version.txt; the file is gitignored.
# The git commit hash is deliberately NOT baked: desktop builds have no .git at
# runtime and the UI hides the hash row when it is absent.
GIT_VERSION="$(git describe --tags --always --dirty 2>/dev/null || echo dev)"
printf '%s' "$GIT_VERSION" > "$REPO_ROOT/build_version.txt"

echo "Building frontend bundle..."
npm run build

echo "Installing desktop build dependencies..."
uv pip install -e ".[server,desktop]"

echo "Packaging desktop app with PyInstaller..."
$PYTHON -m PyInstaller \
    desktop.py \
    --noconfirm \
    --clean \
    --name tono \
    --windowed \
    --onefile \
    --distpath desktop-dist \
    --workpath desktop-build \
    --specpath desktop-build \
    --add-data "${FRONTEND_DIST}:frontend/dist" \
    --add-data "${DEMO_DIR}:demo" \
    --add-data "${REPO_ROOT}/build_version.txt:." \
    --collect-all matplotlib \
    --collect-all scipy \
    --collect-all skimage \
    --collect-all webview \
    --copy-metadata gwyfile

if $CREATE_TAR; then
    TAR_PATH="desktop-dist/tono-linux.tar.gz"
    echo "Creating tarball..."
    tar -czf "$TAR_PATH" -C desktop-dist tono
    echo "Tarball created: $TAR_PATH"
fi

echo "Desktop build complete."
echo "Output: $REPO_ROOT/desktop-dist/"
