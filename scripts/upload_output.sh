#!/usr/bin/env bash
set -eo pipefail

echo "=================================================="
echo "[+] Packaging and Uploading Extracted Images..."
echo "=================================================="

OUTDIR="$(pwd)/output_imgs"
BUILD_ID="ota-extract-$(date +'%Y%m%d-%H%M%S')"
TAG_NAME="build-${BUILD_ID}"
ARCHIVE_NAME="${BUILD_ID}.tar.xz"

if [ ! -d "$OUTDIR" ] || [ -z "$(ls -A "$OUTDIR")" ]; then
    echo "[!] Error: Output directory $OUTDIR is empty!"
    exit 1
fi

cd "$OUTDIR"

echo "[+] Creating compressed tar archive: $ARCHIVE_NAME..."
tar -cJf "../$ARCHIVE_NAME" *.img 2>/dev/null || tar -cJf "../$ARCHIVE_NAME" *

cd ..

echo "Compressed package size:"
ls -lh "$ARCHIVE_NAME"

UPLOAD_TARGET="${UPLOAD_TARGET:-gofile}"

if [ "$UPLOAD_TARGET" == "gofile" ]; then
    echo "[+] Executing GoFile Upload..."
    python3 scripts/upload_gofile.py "$ARCHIVE_NAME" || UPLOAD_TARGET="pixeldrain"
fi

if [ "$UPLOAD_TARGET" == "pixeldrain" ]; then
    echo "[+] Uploading to Pixeldrain..."
    RESPONSE=$(curl -s -F "file=@$ARCHIVE_NAME" https://pixeldrain.com/api/file)
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
    gh release create "$TAG_NAME" "$ARCHIVE_NAME" \
        --title "OTA Extract Output ($BUILD_ID)" \
        --notes "Extracted partition images from OTA update package." || {
            echo "[!] GitHub release creation via gh CLI failed. Fallback to GoFile..."
            python3 scripts/upload_gofile.py "$ARCHIVE_NAME"
        }
fi

echo "=================================================="
echo "[+] Finished Delivery Engine Step!"
echo "=================================================="
