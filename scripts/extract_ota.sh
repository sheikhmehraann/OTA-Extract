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

# Check file type
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
    echo "[!] Warning: Unknown file format ($FILE_TYPE). Attempting 7z payload check..."
    if 7z e -y downloaded_target payload.bin 2>/dev/null; then
        PAYLOAD_FILE="$WORKDIR/payload.bin"
    else
        mv downloaded_target payload.bin
        PAYLOAD_FILE="$WORKDIR/payload.bin"
    fi
fi

# Locate payload dumper binary
DUMPER="$(pwd)/../bin/payload-dumper-go"
if [ ! -f "$DUMPER" ]; then
    DUMPER="$(which payload-dumper-go || which payload-dumper || true)"
fi

if [ -z "$DUMPER" ] || [ ! -f "$DUMPER" ]; then
    echo "[!] Error: payload-dumper-go executable not found!"
    exit 1
fi

echo "[+] Extractor binary: $DUMPER"

if [ "$OTA_TYPE" == "INCREMENTAL" ] || [ "$OTA_TYPE" == "DELTA" ]; then
    echo "=================================================="
    echo "[+] Processing INCREMENTAL / DELTA OTA Payload"
    echo "=================================================="
    if [ -z "$BASE_FIRMWARE_URL" ]; then
        echo "[!] Error: BASE_FIRMWARE_URL must be provided for INCREMENTAL extractions!"
        exit 1
    fi

    echo "[+] Downloading Base Firmware from: $BASE_FIRMWARE_URL"
    if ! aria2c -x 16 -s 16 -k 1M --dir="$BASEDIR" -o "base_fw.zip" "$BASE_FIRMWARE_URL"; then
        curl -sSL -o "$BASEDIR/base_fw.zip" "$BASE_FIRMWARE_URL"
    fi
    
    echo "[+] Extracting base firmware payload..."
    cd "$BASEDIR"
    if 7z l base_fw.zip 2>/dev/null | grep -q "payload.bin"; then
        7z e -y base_fw.zip payload.bin
        "$DUMPER" payload.bin -o "$BASEDIR"
    else
        7z x -y base_fw.zip -o"$BASEDIR"
    fi
    cd "$WORKDIR"

    echo "[+] Executing Incremental Diff Extraction..."
    PART_ARGS=""
    if [ "$PARTITIONS" != "all" ] && [ -n "$PARTITIONS" ]; then
        IFS=',' read -ra PART_ARRAY <<< "$PARTITIONS"
        for p in "${PART_ARRAY[@]}"; do
            PART_ARGS="$PART_ARGS -p $p"
        done
    fi

    "$DUMPER" extract-diff "$PAYLOAD_FILE" --old "$BASEDIR" -o "$OUTDIR" $PART_ARGS || \
    "$DUMPER" "$PAYLOAD_FILE" --old "$BASEDIR" -o "$OUTDIR" $PART_ARGS
else
    echo "=================================================="
    echo "[+] Processing FULL OTA Payload"
    echo "=================================================="
    
    if [ -n "$PAYLOAD_FILE" ] && [ -f "$PAYLOAD_FILE" ]; then
        PART_ARGS=""
        if [ "$PARTITIONS" != "all" ] && [ -n "$PARTITIONS" ]; then
            IFS=',' read -ra PART_ARRAY <<< "$PARTITIONS"
            for p in "${PART_ARRAY[@]}"; do
                PART_ARGS="$PART_ARGS -p $p"
            done
        fi
        "$DUMPER" $PART_ARGS -o "$OUTDIR" "$PAYLOAD_FILE"
    elif [ -f "target_ota.zip" ] && 7z l target_ota.zip 2>/dev/null | grep -q "\.new\.dat"; then
        echo "[+] Legacy DAT/BR OTA detected. Extracting..."
        7z x -y target_ota.zip -o"$WORKDIR/legacy"
        cd "$WORKDIR/legacy"
        for br in *.new.dat.br; do
            if [ -f "$br" ]; then
                echo "Decompressing $br..."
                brotli -d "$br"
            fi
        done
        for dat in *.new.dat; do
            if [ -f "$dat" ]; then
                part_name="${dat%.new.dat}"
                if [ -f "${part_name}.transfer.list" ]; then
                    echo "Converting $dat to $OUTDIR/${part_name}.img..."
                    python3 "$(pwd)/../../bin/sdat2img.py" "${part_name}.transfer.list" "$dat" "$OUTDIR/${part_name}.img"
                fi
            fi
        done
    else
        echo "[!] Error: No valid payload.bin or legacy system.new.dat files found to extract!"
        exit 1
    fi
fi

echo "=================================================="
echo "[+] Extraction Complete! Partition files in output_imgs:"
ls -lh "$OUTDIR"
echo "=================================================="
