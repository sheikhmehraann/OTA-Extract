#!/usr/bin/env bash
set -eo pipefail

echo "=================================================="
echo "[+] Starting Android OTA Payload Extraction..."
echo "=================================================="

OTA_URL="${OTA_URL:-}"
OTA_TYPE="${OTA_TYPE:-FULL}"
BASE_FIRMWARE_URL="${BASE_FIRMWARE_URL:-}"
PARTITIONS="${PARTITIONS:-all}"

WORKDIR="$(pwd)/work"
BASEDIR="$(pwd)/base_imgs"
OUTDIR="$(pwd)/output_imgs"

mkdir -p "$WORKDIR" "$BASEDIR" "$OUTDIR"

if [ -z "$OTA_URL" ]; then
    echo "[!] Error: OTA_URL is empty!"
    exit 1
fi

echo "=================================================="
echo "[+] Checking for Full OTA Upgrade via Google Check-in..."
echo "=================================================="
RESOLVED_URL=$(python3 scripts/resolve_full_ota.py "$OTA_URL" | grep "\[FINAL_URL\]" | awk '{print $2}' || true)
if [ -n "$RESOLVED_URL" ] && [[ "$RESOLVED_URL" == http* ]]; then
    echo "[+] Using Resolved URL: $RESOLVED_URL"
    OTA_URL="$RESOLVED_URL"
fi

echo "[+] Downloading target OTA from: $OTA_URL"
cd "$WORKDIR"

if ! aria2c -x 16 -s 16 -k 1M --dir="$WORKDIR" -o "downloaded_target" "$OTA_URL"; then
    echo "[!] aria2c download failed, falling back to curl..."
    curl -sSL -o "downloaded_target" "$OTA_URL"
fi

if [ ! -f "downloaded_target" ] || [ ! -s "downloaded_target" ]; then
    echo "[!] Error: Downloaded file is missing or zero bytes!"
    exit 1
fi

PAYLOAD_FILE=""
FILE_TYPE=$(file "downloaded_target" || true)

if 7z l downloaded_target >/dev/null 2>&1 && 7z l downloaded_target | grep -q "payload.bin"; then
    echo "[+] Found payload.bin inside downloaded ZIP archive. Extracting..."
    7z e -y downloaded_target payload.bin
    PAYLOAD_FILE="$WORKDIR/payload.bin"
elif [[ "$FILE_TYPE" == *"Zip archive"* ]] || [[ "$FILE_TYPE" == *"7-zip archive"* ]]; then
    echo "[+] Downloaded file is a ZIP archive without payload.bin. Checking for legacy dat/br images..."
    mv downloaded_target target_ota.zip
elif [[ "$OTA_URL" == *"payload.bin"* ]] || [[ "$FILE_TYPE" == *"data"* ]]; then
    echo "[+] Direct payload.bin file detected."
    mv downloaded_target payload.bin
    PAYLOAD_FILE="$WORKDIR/payload.bin"
else
    echo "[+] Attempting 7z payload check..."
    if 7z e -y downloaded_target payload.bin 2>/dev/null; then
        PAYLOAD_FILE="$WORKDIR/payload.bin"
    else
        mv downloaded_target payload.bin
        PAYLOAD_FILE="$WORKDIR/payload.bin"
    fi
fi

# Base firmware handling if provided
if [ -n "$BASE_FIRMWARE_URL" ]; then
    echo "=================================================="
    echo "[+] Base Firmware URL provided: $BASE_FIRMWARE_URL"
    echo "=================================================="
    echo "[+] Downloading Base Firmware..."
    if ! aria2c -x 16 -s 16 -k 1M --dir="$BASEDIR" -o "base_fw.zip" "$BASE_FIRMWARE_URL"; then
        curl -sSL -o "$BASEDIR/base_fw.zip" "$BASE_FIRMWARE_URL"
    fi
    echo "[+] Unpacking Base Firmware..."
    cd "$BASEDIR"
    if 7z l base_fw.zip 2>/dev/null | grep -q "payload.bin"; then
        7z e -y base_fw.zip payload.bin
        "$(pwd)/../../bin/payload-dumper-go" -o "$BASEDIR" payload.bin || true
    else
        7z x -y base_fw.zip -o"$BASEDIR" || true
    fi
    cd "$WORKDIR"
fi

cd "$(pwd)/.."

echo "=================================================="
echo "[+] Executing Auto Incremental Resolver Engine..."
echo "=================================================="

python3 scripts/auto_incremental_resolver.py "$PAYLOAD_FILE" "$OUTDIR" "$BASEDIR"

echo "=================================================="
echo "[+] Extraction Complete! Partition files in output_imgs:"
ls -lh "$OUTDIR"
echo "=================================================="
