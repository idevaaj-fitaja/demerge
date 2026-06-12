#!/bin/bash
set -e

cd "$(dirname "$0")"
ROOT_DIR="$(cd "$(dirname "$PWD")" && pwd)"
OUT_DIR="$PWD/out"
APP_NAME="Demerge"
APP_DIR="$OUT_DIR/$APP_NAME.app"
RES="$APP_DIR/Contents/Resources"

echo "=== Building frontend ==="
cd "$ROOT_DIR/frontend" && npm run build && cd "$ROOT_DIR/electron"

echo "=== Creating app bundle ==="
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"
cp -R node_modules/electron/dist/Electron.app "$APP_DIR"

echo "=== Electron JS ==="
mkdir -p "$RES/app"
cp main.js preload.js loading.html "$RES/app/"
cat > "$RES/app/package.json" << 'EOF'
{"name":"demerge","productName":"Demerge","main":"main.js"}
EOF

echo "=== Python venv ==="
cp -R "$ROOT_DIR/venv-minimal" "$RES/venv-minimal"
chmod +x "$RES/venv-minimal/bin/python"

rm -rf "$RES/venv-minimal/lib/python3.14/site-packages/pip"
rm -rf "$RES/venv-minimal/lib/python3.14/site-packages/"*.dist-info
rm -rf "$RES/venv-minimal/lib/python3.14/site-packages/__pycache__"
rm -f "$RES/venv-minimal/bin/"{activate,activate.csh,activate.fish,Activate.ps1,pip,pip3,pip3.14,watchfiles,websockets,idna}
rm -rf "$RES/venv-minimal/include"

echo "=== Backend ==="
cp "$ROOT_DIR/run.py" "$RES/"
mkdir -p "$RES/backend"
for item in "$ROOT_DIR/backend/"*; do
  cp -R "$item" "$RES/backend/"
done

echo "=== Frontend dist ==="
mkdir -p "$RES/frontend"
cp -R "$ROOT_DIR/frontend/dist" "$RES/frontend/dist"

echo "=== Fix main.js ==="
sed -i '' 's|const isDev = !app.isPackaged;|const isDev = false;|g' "$RES/app/main.js"

echo "=== Info.plist ==="
cat > "$APP_DIR/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>Electron</string>
  <key>CFBundleIdentifier</key>
  <string>com.demerge.app</string>
  <key>CFBundleName</key>
  <string>Demerge</string>
  <key>CFBundleDisplayName</key>
  <string>Demerge</string>
  <key>CFBundleVersion</key>
  <string>1.0.0</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0.0</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSMinimumSystemVersion</key>
  <string>10.15</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
EOF

echo "=== Optimizing ==="
FW="$APP_DIR/Contents/Frameworks/Electron Framework.framework/Versions/A"
LOCALES="$FW/Resources"
for dir in "$LOCALES"/*.lproj; do
  base=$(basename "$dir" .lproj)
  [[ "$base" == "en" || "$base" == "id" ]] || rm -rf "$dir"
done
for dir in "$RES"/*.lproj; do
  base=$(basename "$dir" .lproj)
  [[ "$base" == "en" || "$base" == "id" ]] || rm -rf "$dir"
done
rm -f "$FW/Libraries/libvk_swiftshader.dylib" "$FW/Libraries/vk_swiftshader_icd.json"
rm -f "$RES/electron.icns" "$RES/default_app.asar"

echo "=== Done ==="
du -sh "$APP_DIR"
echo "App: $APP_DIR"
