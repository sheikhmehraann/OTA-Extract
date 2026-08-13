#!/usr/bin/env bash
set -eo pipefail

echo "[+] Setting up dependencies & binaries..."
sudo apt-get update -qq
sudo apt-get install -y aria2 p7zip-full brotli python3 python3-pip curl jq xz-utils

TOOLS_DIR="$(pwd)/bin"
mkdir -p "$TOOLS_DIR"

echo "[+] Downloading payload-dumper-go..."
PAYLOAD_DUMPER_URL=$(curl -s https://api.github.com/repos/xishang0128/payload-dumper-go/releases/latest | jq -r '.assets[] | select(.name | contains("linux_amd64")) | .browser_download_url')

if [ -z "$PAYLOAD_DUMPER_URL" ] || [ "$PAYLOAD_DUMPER_URL" == "null" ]; then
    PAYLOAD_DUMPER_URL="https://github.com/ssut/payload-dumper-go/releases/download/1.2.2/payload-dumper-go_1.2.2_linux_amd64.tar.gz"
fi

echo "Fetching from: $PAYLOAD_DUMPER_URL"
curl -sL "$PAYLOAD_DUMPER_URL" -o "$TOOLS_DIR/payload-dumper.tar.gz" || curl -sL "$PAYLOAD_DUMPER_URL" -o "$TOOLS_DIR/payload-dumper"

if [ -f "$TOOLS_DIR/payload-dumper.tar.gz" ]; then
    tar -xzf "$TOOLS_DIR/payload-dumper.tar.gz" -C "$TOOLS_DIR" payload-dumper-go || tar -xzf "$TOOLS_DIR/payload-dumper.tar.gz" -C "$TOOLS_DIR"
    rm -f "$TOOLS_DIR/payload-dumper.tar.gz"
fi

chmod +x "$TOOLS_DIR/payload-dumper-go" 2>/dev/null || chmod +x "$TOOLS_DIR/payload-dumper" 2>/dev/null || true

echo "[+] Downloading sdat2img helper..."
curl -sL "https://raw.githubusercontent.com/xpirt/sdat2img/master/sdat2img.py" -o "$TOOLS_DIR/sdat2img.py"
chmod +x "$TOOLS_DIR/sdat2img.py"

echo "[+] Tools successfully installed in $TOOLS_DIR!"
