#!/bin/bash
# Build Demerge for Windows from macOS
# Usage: ./scripts/build-win.sh
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ELECTRON_DIR="$ROOT_DIR/electron"
VENV_MINIMAL="$ROOT_DIR/venv-minimal"
VENV_WIN="$ROOT_DIR/venv-win"
BACKUP_VENV="$ROOT_DIR/venv-minimal.bak"

echo "=== Building Demerge for Windows ==="
echo ""

# Step 1: Build frontend
echo ">>> [1/4] Building frontend..."
cd "$ROOT_DIR/frontend"
npm run build
echo "  Frontend built successfully"
echo ""

# Step 2: Ensure Windows venv exists
echo ">>> [2/4] Checking Windows venv..."
if [ ! -d "$VENV_WIN" ] || [ ! -f "$VENV_WIN/Scripts/python.exe" ]; then
    echo "  Windows venv not found. Creating it..."
    cd "$ROOT_DIR"
    python3 scripts/build_win_venv.py
else
    echo "  Windows venv exists at $VENV_WIN"
fi
echo ""

# Step 3: Swap venv (backup macOS venv, use Windows venv)
echo ">>> [3/4] Swapping venv for Windows build..."
if [ -d "$VENV_MINIMAL" ]; then
    echo "  Backing up venv-minimal -> venv-minimal.bak"
    rm -rf "$BACKUP_VENV"
    mv "$VENV_MINIMAL" "$BACKUP_VENV"
fi
echo "  Copying venv-win -> venv-minimal"
cp -R "$VENV_WIN" "$VENV_MINIMAL"
echo "  Check: $(ls "$VENV_MINIMAL/Scripts/"python*.exe 2>/dev/null || echo 'NO python.exe found!')"
echo ""

# Step 4: Build Windows installer
echo ">>> [4/4] Building Windows installer with electron-builder..."
cd "$ELECTRON_DIR"
npm run build:win
BUILD_EXIT=$?

# Restore original venv
echo ""
echo ">>> Restoring original venv..."
rm -rf "$VENV_MINIMAL"
if [ -d "$BACKUP_VENV" ]; then
    mv "$BACKUP_VENV" "$VENV_MINIMAL"
    echo "  Restored venv-minimal from backup"
fi

if [ $BUILD_EXIT -eq 0 ]; then
    echo ""
    echo "=== SUCCESS ==="
    echo "Windows installer: $ELECTRON_DIR/dist-bundle/Demerge-*.exe"
    ls -lh "$ELECTRON_DIR/dist-bundle/"*.exe 2>/dev/null || echo "  (check dist-bundle/ for output)"
else
    echo ""
    echo "=== BUILD FAILED (exit code $BUILD_EXIT) ==="
    exit $BUILD_EXIT
fi
