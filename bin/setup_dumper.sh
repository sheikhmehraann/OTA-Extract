#!/usr/bin/env bash
set -eo pipefail

echo "=================================================="
echo "[+] Setting up High-Performance Dependencies..."
echo "=================================================="

sudo apt-get update -qq
sudo apt-get install -y aria2 p7zip-full brotli python3 python3-pip python3-setuptools curl jq xz-utils libssl-dev

echo "[+] Installing Python payload extraction requirements..."
python3 -m pip install --break-system-packages protobuf bsdiff4 brotli fsspec zstandard || pip3 install protobuf bsdiff4 brotli fsspec zstandard || true

TOOLS_DIR="$(pwd)/bin"
mkdir -p "$TOOLS_DIR"

chmod +x "$TOOLS_DIR/payload-extract" 2>/dev/null || true

# Setup payload-dumper-go
echo "[+] Setting up payload-dumper-go..."
PAYLOAD_DUMPER_URL=$(curl -s https://api.github.com/repos/xishang0128/payload-dumper-go/releases/latest | jq -r '.assets[] | select(.name | contains("linux_amd64")) | .browser_download_url' 2>/dev/null || true)

if [ -z "$PAYLOAD_DUMPER_URL" ] || [ "$PAYLOAD_DUMPER_URL" == "null" ]; then
    PAYLOAD_DUMPER_URL="https://github.com/ssut/payload-dumper-go/releases/download/1.2.2/payload-dumper-go_1.2.2_linux_amd64.tar.gz"
fi

curl -sL "$PAYLOAD_DUMPER_URL" -o "$TOOLS_DIR/payload-dumper.tar.gz" || curl -sL "$PAYLOAD_DUMPER_URL" -o "$TOOLS_DIR/payload-dumper"

if [ -f "$TOOLS_DIR/payload-dumper.tar.gz" ]; then
    tar -xzf "$TOOLS_DIR/payload-dumper.tar.gz" -C "$TOOLS_DIR" payload-dumper-go 2>/dev/null || tar -xzf "$TOOLS_DIR/payload-dumper.tar.gz" -C "$TOOLS_DIR" 2>/dev/null || true
    rm -f "$TOOLS_DIR/payload-dumper.tar.gz"
fi

chmod +x "$TOOLS_DIR/payload-dumper-go" 2>/dev/null || true

# Setup Python payload_dumper fallback scripts
echo "[+] Setting up Python payload_dumper..."
curl -sL "https://raw.githubusercontent.com/vm03/payload_dumper/master/payload_dumper.py" -o "$TOOLS_DIR/payload_dumper.py"
curl -sL "https://raw.githubusercontent.com/vm03/payload_dumper/master/update_metadata_pb2.py" -o "$TOOLS_DIR/update_metadata_pb2.py"
curl -sL "https://raw.githubusercontent.com/xpirt/sdat2img/master/sdat2img.py" -o "$TOOLS_DIR/sdat2img.py"

echo "=================================================="
echo "[+] Tools successfully installed in $TOOLS_DIR!"
ls -lh "$TOOLS_DIR"
echo "=================================================="
