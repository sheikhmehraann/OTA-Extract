#!/usr/bin/env bash
set -eo pipefail

echo "=================================================="
echo "[+] Cleaning runner disk space..."
echo "=================================================="

echo "Initial disk space:"
df -h /

echo "[+] Removing large unused software packages..."
sudo rm -rf /usr/share/dotnet
sudo rm -rf /usr/local/lib/android
sudo rm -rf /opt/ghc
sudo rm -rf /opt/hostedtoolcache/CodeQL
sudo rm -rf /usr/local/share/powershell
sudo rm -rf /usr/local/share/chromium
sudo rm -rf /usr/local/share/vcpkg

echo "[+] Purging Docker images..."
sudo docker image prune --all --force || true

echo "Final disk space available:"
df -h /
echo "=================================================="
