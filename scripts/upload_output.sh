#!/usr/bin/env bash
set -eo pipefail

echo "=================================================="
echo "[+] Packaging and Uploading Extracted Images..."
echo "=================================================="

OUTDIR="$(pwd)/output_imgs"
BUILD_ID="ota-extract-$(date +'%Y%m%d-%H%M%S')"
TAG_NAME="build-${BUILD_ID}"
ZIP_NAME="${BUILD_ID}.zip"

if [ ! -d "$OUTDIR" ] || [ -z "$(ls -A "$OUTDIR")" ]; then
    echo "[!] Error: Output directory $OUTDIR is empty!"
    exit 1
fi

cd "$OUTDIR"

echo "[+] Creating output ZIP archive: $ZIP_NAME..."
7z a -tzip "../$ZIP_NAME" *.img 2>/dev/null || zip -r "../$ZIP_NAME" .

cd ..

echo "Compressed package details:"
ls -lh "$ZIP_NAME"

UPLOAD_TARGET="${UPLOAD_TARGET:-gofile}"

echo "[+] Uploading $ZIP_NAME to $UPLOAD_TARGET..."

if [ "$UPLOAD_TARGET" == "gofile" ] || [ "$UPLOAD_TARGET" == "all" ]; then
    echo "[+] Uploading to GoFile..."
    python3 scripts/upload_gofile.py "$ZIP_NAME" || {
        echo "[!] GoFile upload failed, falling back to Pixeldrain..."
        UPLOAD_TARGET="pixeldrain"
    }
fi

if [ "$UPLOAD_TARGET" == "pixeldrain" ]; then
    echo "[+] Uploading to Pixeldrain..."
    RESPONSE=$(curl -s -F "file=@$ZIP_NAME" https://pixeldrain.com/api/file)
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
    gh release create "$TAG_NAME" "$ZIP_NAME" \
        --title "OTA Extract Output ($BUILD_ID)" \
        --notes "Extracted partition images from OTA update package." || {
            echo "[!] GitHub release creation failed. Uploading to GoFile fallback..."
            python3 scripts/upload_gofile.py "$ZIP_NAME"
        }
fi

echo "=================================================="
echo "[+] Delivery Engine Finished Successfully!"
echo "=================================================="
