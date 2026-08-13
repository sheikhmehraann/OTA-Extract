#!/usr/bin/env python3
"""
Auto Incremental Payload Resolver Engine
Reconstructs real partition images directly from raw data blocks in Incremental OTAs.
"""

import os
import sys
import subprocess

try:
    from raw_block_extractor import extract_raw_blocks
except ImportError:
    from scripts.raw_block_extractor import extract_raw_blocks

def resolve_incremental(payload_path, output_dir, base_dir=None):
    os.makedirs(output_dir, exist_ok=True)
    rust_dumper = os.path.abspath("bin/payload-extract")
    go_dumper = os.path.abspath("bin/payload-dumper-go")
    py_dumper = os.path.abspath("bin/payload_dumper.py")

    print("==================================================")
    print("[+] Auto Incremental Resolver Engine Initiated")
    print(f"[+] Target Payload: {payload_path}")
    print("==================================================")

    # 1. Engine #1: Universal Raw Block Extractor (Reconstructs ALL partition images)
    print("[+] Engine 1: Executing Universal Raw Protobuf Block Extractor...")
    try:
        extract_raw_blocks(payload_path, output_dir)
    except Exception as e:
        print(f"[!] Raw Block Extractor Warning: {e}")

    # 2. Engine #2: YuKongA payload-extract Rust Engine if base directory exists
    if base_dir and os.path.exists(base_dir) and os.listdir(base_dir) and os.path.exists(rust_dumper) and os.access(rust_dumper, os.X_OK):
        print("\n[+] Engine 2: Executing YuKongA payload-extract (Rust) with base firmware...")
        cmd = [rust_dumper, "extract", payload_path, "-o", output_dir, "--source-dir", base_dir]
        subprocess.run(cmd, check=False)

    # 3. Engine #3: payload-dumper-go
    if os.path.exists(go_dumper) and os.access(go_dumper, os.X_OK):
        print("\n[+] Engine 3: Executing payload-dumper-go...")
        cmd = [go_dumper, "-o", output_dir, payload_path]
        subprocess.run(cmd, check=False)

    # 4. Engine #4: Python payload_dumper
    if os.path.exists(py_dumper):
        print("\n[+] Engine 4: Executing Python payload_dumper...")
        cmd = ["python3", py_dumper, "--out", output_dir, payload_path]
        subprocess.run(cmd, check=False)

    # 5. Filter & Keep all valid partition files (> 0 bytes)
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
                print(f"  [-] Removing 0-byte placeholder: {fname}")
                os.remove(fpath)
            else:
                valid_images.append(fname)
                total_bytes += size
                print(f"  [✓] EXTRACTED REAL PARTITION IMAGE: {fname:<25} ({size / 1024 / 1024:.2f} MB)")

    print("==================================================")
    print(f"[SUCCESS] Total Extracted Partition Images: {len(valid_images)} ({total_bytes / 1024 / 1024:.2f} MB total)")
    print("==================================================")

    if not valid_images:
        print("[!] Error: No partition images could be extracted.")
        sys.exit(1)

if __name__ == "__main__":
    p_file = sys.argv[1] if len(sys.argv) > 1 else "work/payload.bin"
    o_dir = sys.argv[2] if len(sys.argv) > 2 else "output_imgs"
    b_dir = sys.argv[3] if len(sys.argv) > 3 else "base_imgs"
    resolve_incremental(p_file, o_dir, b_dir)
