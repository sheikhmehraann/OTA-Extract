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
aria2c -x 16 -s 16 -k 1M --dir="$WORKDIR" -o "target_ota.zip" "$OTA_URL" || curl -sL "$OTA_URL" -o "$WORKDIR/target_ota.zip"

echo "[+] Inspecting downloaded file..."
cd "$WORKDIR"

PAYLOAD_FILE=""
if 7z l target_ota.zip | grep -q "payload.bin"; then
    echo "[+] Found payload.bin in target OTA zip. Extracting..."
    7z e -y target_ota.zip payload.bin
    PAYLOAD_FILE="$WORKDIR/payload.bin"
elif [ -f "target_ota.zip" ] && file "target_ota.zip" | grep -q "data"; then
    # File might be payload.bin directly
    mv target_ota.zip payload.bin
    PAYLOAD_FILE="$WORKDIR/payload.bin"
fi

# Locate payload dumper executable
DUMPER="$(pwd)/../bin/payload-dumper-go"
if [ ! -f "$DUMPER" ]; then
    DUMPER="$(which payload-dumper-go || which payload-dumper || true)"
fi

if [ -z "$DUMPER" ]; then
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
    aria2c -x 16 -s 16 -k 1M --dir="$BASEDIR" -o "base_fw.zip" "$BASE_FIRMWARE_URL" || curl -sL "$BASE_FIRMWARE_URL" -o "$BASEDIR/base_fw.zip"
    
    echo "[+] Extracting base firmware payload..."
    cd "$BASEDIR"
    if 7z l base_fw.zip | grep -q "payload.bin"; then
        7z e -y base_fw.zip payload.bin
        "$DUMPER" payload.bin -o "$BASEDIR"
    else
        7z x -y base_fw.zip -o"$BASEDIR"
    fi
    cd "$WORKDIR"

    echo "[+] Executing Incremental Diff Extraction..."
    if [ "$PARTITIONS" != "all" ] && [ -n "$PARTITIONS" ]; then
        PART_ARG="-p $PARTITIONS"
    else
        PART_ARG=""
    fi

    "$DUMPER" extract-diff "$PAYLOAD_FILE" --old "$BASEDIR" -o "$OUTDIR" $PART_ARG || \
    "$DUMPER" "$PAYLOAD_FILE" --old "$BASEDIR" -o "$OUTDIR" $PART_ARG
else
    echo "=================================================="
    echo "[+] Processing FULL OTA Payload"
    echo "=================================================="
    
    if [ -n "$PAYLOAD_FILE" ] && [ -f "$PAYLOAD_FILE" ]; then
        if [ "$PARTITIONS" != "all" ] && [ -n "$PARTITIONS" ]; then
            IFS=',' read -ra PART_ARRAY <<< "$PARTITIONS"
            PART_ARGS=""
            for p in "${PART_ARRAY[@]}"; do
                PART_ARGS="$PART_ARGS -p $p"
            done
            "$DUMPER" $PART_ARGS -o "$OUTDIR" "$PAYLOAD_FILE"
        else
            "$DUMPER" -o "$OUTDIR" "$PAYLOAD_FILE"
        fi
    elif 7z l target_ota.zip | grep -q "\.new\.dat"; then
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
    fi
fi

echo "=================================================="
echo "[+] Extraction Complete! Partition files in output_imgs:"
ls -lh "$OUTDIR"
echo "=================================================="
