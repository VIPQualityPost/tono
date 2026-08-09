#!/usr/bin/env bash
set -euo pipefail

CREATE_DMG=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-dmg)   CREATE_DMG=false; shift ;;
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
    --copy-metadata gwyfile \
    --icon ../resources/icon.icns

APP_BUNDLE="desktop-dist/tono.app"

if [ ! -d "$APP_BUNDLE" ]; then
    # --onedir puts it inside a folder
    if [ -d "desktop-dist/tono/tono.app" ]; then
        APP_BUNDLE="desktop-dist/tono/tono.app"
    else
        echo "Warning: .app bundle not found; skipping DMG creation."
        CREATE_DMG=false
    fi
fi

if $CREATE_DMG; then
    DMG_PATH="desktop-dist/tono.dmg"
    echo "Creating DMG installer..."
    rm -f "$DMG_PATH"

    # Create a temporary directory for DMG contents
    DMG_STAGING="desktop-build/dmg-staging"
    rm -rf "$DMG_STAGING"
    mkdir -p "$DMG_STAGING"
    cp -R "$APP_BUNDLE" "$DMG_STAGING/"
    ln -s /Applications "$DMG_STAGING/Applications"

    hdiutil create \
        -volname "tono" \
        -srcfolder "$DMG_STAGING" \
        -ov \
        -format UDZO \
        "$DMG_PATH"

    rm -rf "$DMG_STAGING"
    echo "DMG created: $DMG_PATH"
fi

echo "Desktop build complete."
echo "Output: $REPO_ROOT/desktop-dist/"
