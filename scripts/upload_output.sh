#!/usr/bin/env bash
set -eo pipefail

echo "=================================================="
echo "[+] Packaging and Delivering Extracted Images..."
echo "=================================================="

OUTDIR="$(pwd)/output_imgs"
BUILD_ID="ota-extract-$(date +'%Y%m%d-%H%M%S')"
TAG_NAME="build-${BUILD_ID}"
ARCHIVE_FORMAT="${ARCHIVE_FORMAT:-tar.zst}"

if [ ! -d "$OUTDIR" ] || [ -z "$(ls -A "$OUTDIR")" ]; then
    echo "[!] Error: Output directory $OUTDIR is empty!"
    exit 1
fi

cd "$OUTDIR"

if [ "$ARCHIVE_FORMAT" == "zip" ]; then
    PKG_NAME="${BUILD_ID}.zip"
    echo "[+] Creating standard ZIP archive: $PKG_NAME..."
    7z a -tzip "../$PKG_NAME" *.img 2>/dev/null || zip -r "../$PKG_NAME" .
else
    PKG_NAME="${BUILD_ID}-images.tar.zst"
    echo "[+] Creating high-speed Rama-style Zstandard archive: $PKG_NAME..."
    tar -cf - *.img | zstd -T0 -19 -o "../$PKG_NAME"
fi

cd ..

echo "Compressed package details:"
ls -lh "$PKG_NAME"

UPLOAD_TARGET="${UPLOAD_TARGET:-gofile}"

echo "[+] Uploading $PKG_NAME to $UPLOAD_TARGET..."

if [ "$UPLOAD_TARGET" == "gofile" ] || [ "$UPLOAD_TARGET" == "all" ]; then
    echo "[+] Uploading to GoFile..."
    python3 scripts/upload_gofile.py "$PKG_NAME" || {
        echo "[!] GoFile upload failed, falling back to Pixeldrain..."
        UPLOAD_TARGET="pixeldrain"
    }
fi

if [ "$UPLOAD_TARGET" == "pixeldrain" ]; then
    echo "[+] Uploading to Pixeldrain..."
    RESPONSE=$(curl -s -F "file=@$PKG_NAME" https://pixeldrain.com/api/file)
    FILE_ID=$(echo "$RESPONSE" | jq -r '.id')
    if [ -n "$FILE_ID" ] && [ "$FILE_ID" != "null" ]; then
        echo "=================================================="
        echo "[SUCCESS] Pixeldrain Download URL: https://pixeldrain.com/u/$FILE_ID"
        echo "=================================================="
    else
        echo "[!] Pixeldrain upload failed: $RESPONSE"
    fi
fi

if [ "$UPLOAD_TARGET" == "release" ] || [ "$UPLOAD_TARGET" == "github" ]; then
    echo "[+] Creating GitHub Release tag $TAG_NAME..."
    gh release create "$TAG_NAME" "$PKG_NAME" \
        --title "OTA Extract Output ($BUILD_ID)" \
        --notes "Extracted partition images from OTA update package." || {
            echo "[!] GitHub release creation failed. Uploading to GoFile fallback..."
            python3 scripts/upload_gofile.py "$PKG_NAME"
        }
fi

echo "=================================================="
echo "[+] Delivery Engine Finished Successfully!"
echo "=================================================="
