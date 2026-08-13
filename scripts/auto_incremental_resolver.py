#!/usr/bin/env python3
"""
Auto Incremental Payload Resolver Engine
Extracts full replacement partition images and resolves matching base payloads.
"""

import os
import sys
import shutil
import subprocess

def resolve_incremental(payload_path, output_dir, base_dir=None):
    os.makedirs(output_dir, exist_ok=True)
    rust_dumper = os.path.abspath("bin/payload-extract")
    go_dumper = os.path.abspath("bin/payload-dumper-go")
    py_dumper = os.path.abspath("bin/payload_dumper.py")

    print("==================================================")
    print("[+] Auto Incremental Resolver Engine Initiated")
    print(f"[+] Target Payload: {payload_path}")
    if base_dir and os.path.exists(base_dir) and os.listdir(base_dir):
        print(f"[+] Base Firmware Directory: {base_dir}")
    else:
        print("[!] No base directory supplied — executing multi-engine extraction...")
    print("==================================================")

    # 1. Engine #1: YuKongA payload-extract (Rust)
    if os.path.exists(rust_dumper) and os.access(rust_dumper, os.X_OK):
        print("[+] Engine 1: Executing YuKongA payload-extract (Rust)...")
        if base_dir and os.path.exists(base_dir) and os.listdir(base_dir):
            cmd = [rust_dumper, "extract", payload_path, "-o", output_dir, "--source-dir", base_dir]
        else:
            cmd = [rust_dumper, "extract", payload_path, "-o", output_dir]
        res = subprocess.run(cmd, check=False)

    # 2. Engine #2: payload-dumper-go (Go)
    if os.path.exists(go_dumper) and os.access(go_dumper, os.X_OK):
        print("\n[+] Engine 2: Executing payload-dumper-go...")
        cmd = [go_dumper, "-o", output_dir, payload_path]
        subprocess.run(cmd, check=False)

    # 3. Engine #3: Python payload_dumper
    if os.path.exists(py_dumper):
        print("\n[+] Engine 3: Executing Python payload_dumper...")
        cmd = ["python3", py_dumper, "--out", output_dir, payload_path]
        subprocess.run(cmd, check=False)

    # 4. Filter & Keep all valid partition files (> 0 bytes)
    print("\n==================================================")
    print("[+] Validating Extracted Partition Images...")
    print("==================================================")

    valid_images = []
    total_bytes = 0

    for fname in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            if size == 0:
                print(f"  [-] Removing 0-byte file: {fname}")
                os.remove(fpath)
            else:
                valid_images.append(fname)
                total_bytes += size
                print(f"  [✓] EXTRACTED PARTITION: {fname:<25} ({size / 1024 / 1024:.2f} MB)")

    print("==================================================")
    print(f"[SUCCESS] Total Extracted Partition Files: {len(valid_images)} ({total_bytes / 1024 / 1024:.2f} MB total)")
    print("==================================================")

    if not valid_images:
        print("[!] Error: No partition images could be extracted.")
        sys.exit(1)

if __name__ == "__main__":
    p_file = sys.argv[1] if len(sys.argv) > 1 else "work/payload.bin"
    o_dir = sys.argv[2] if len(sys.argv) > 2 else "output_imgs"
    b_dir = sys.argv[3] if len(sys.argv) > 3 else "base_imgs"
    resolve_incremental(p_file, o_dir, b_dir)
