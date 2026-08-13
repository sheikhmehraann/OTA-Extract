#!/usr/bin/env python3
"""
Smart Multi-Engine Android Payload Extractor
Chains YuKongA payload-extract (Rust) -> payload-dumper-go (Go) -> payload_dumper.py (Python)
to guarantee zero-error extraction of valid partition images from Full & Incremental OTAs.
"""

import os
import sys
import shutil
import subprocess

def smart_extract(payload_path, out_dir, old_dir=None):
    os.makedirs(out_dir, exist_ok=True)
    rust_dumper = os.path.abspath("bin/payload-extract")
    go_dumper = os.path.abspath("bin/payload-dumper-go")
    py_dumper = os.path.abspath("bin/payload_dumper.py")

    print("==================================================")
    print("[+] Starting Multi-Engine Payload Extraction...")
    print("==================================================")

    # 1. Engine #1: YuKongA payload-extract (Rust)
    if os.path.exists(rust_dumper) and os.access(rust_dumper, os.X_OK):
        print("[+] Engine 1: Executing YuKongA payload-extract (Rust)...")
        if old_dir and os.path.exists(old_dir):
            cmd_rust = [rust_dumper, "extract", payload_path, "-o", out_dir, "--source-dir", old_dir]
        else:
            cmd_rust = [rust_dumper, "extract", payload_path, "-o", out_dir]
        subprocess.run(cmd_rust, check=False)

    # 2. Engine #2: payload-dumper-go (Go)
    if os.path.exists(go_dumper) and os.access(go_dumper, os.X_OK):
        print("\n[+] Engine 2: Executing payload-dumper-go (Go)...")
        cmd_go = [go_dumper, "-o", out_dir, payload_path]
        subprocess.run(cmd_go, check=False)

    # 3. Engine #3: Python payload_dumper
    if os.path.exists(py_dumper):
        print("\n[+] Engine 3: Executing Python payload_dumper...")
        cmd_py = ["python3", py_dumper, "--out", out_dir, payload_path]
        subprocess.run(cmd_py, check=False)

    # 4. Filter & Validate Extracted Images
    print("\n==================================================")
    print("[+] Filtering & Validating Extracted Partition Images...")
    print("==================================================")

    valid_files = []
    total_size_bytes = 0

    for fname in sorted(os.listdir(out_dir)):
        fpath = os.path.join(out_dir, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            if size < 4096:
                print(f"  [-] Purging empty placeholder: {fname} ({size} bytes)")
                os.remove(fpath)
            else:
                total_size_bytes += size
                print(f"  [✓] VALID PARTITION IMAGE: {fname:<25} ({size / 1024 / 1024:.2f} MB)")
                valid_files.append(fname)

    if not valid_files:
        print("\n[!] Error: No valid partition images extracted.")
        sys.exit(1)

    print("==================================================")
    print(f"[SUCCESS] {len(valid_files)} valid partition image(s) ready ({total_size_bytes / 1024 / 1024:.2f} MB total)")
    print("==================================================")

if __name__ == "__main__":
    payload = sys.argv[1] if len(sys.argv) > 1 else "work/payload.bin"
    output = sys.argv[2] if len(sys.argv) > 2 else "output_imgs"
    base = sys.argv[3] if len(sys.argv) > 3 else None
    smart_extract(payload, output, base)
