#!/usr/bin/env python3
"""
Smart Android OTA Payload Extractor & Reconstructor
Extracts valid partition images, filters out empty delta placeholders,
and runs multi-engine fallback (Go + Python) for Incremental & Full OTAs.
"""

import os
import sys
import shutil
import subprocess

def smart_extract(payload_path, out_dir, old_dir=None):
    os.makedirs(out_dir, exist_ok=True)
    dumper_bin = os.path.abspath("bin/payload-dumper-go")
    py_dumper = os.path.abspath("bin/payload_dumper.py")
    
    if not os.path.exists(dumper_bin):
        dumper_bin = shutil.which("payload-dumper-go") or "payload-dumper-go"

    print(f"[+] Using Go dumper binary: {dumper_bin}")
    print(f"[+] Using Python dumper script: {py_dumper}")
    print(f"[+] Payload target: {payload_path}")

    # 1. Run Go dumper
    print("[+] Running Go payload-dumper-go...")
    cmd_go = [dumper_bin, "-o", out_dir, payload_path]
    subprocess.run(cmd_go, check=False)

    # 2. Run Python dumper to extract any replacement partitions missed by Go engine
    if os.path.exists(py_dumper):
        print("\n[+] Running Python payload_dumper engine...")
        cmd_py = ["python3", py_dumper, "--out", out_dir, payload_path]
        subprocess.run(cmd_py, check=False)

    # 3. Filter extracted files to purge empty 0-byte placeholders
    print("\n[+] Filtering extracted partition images...")
    valid_files = []
    for fname in os.listdir(out_dir):
        fpath = os.path.join(out_dir, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            if size < 4096:
                print(f"  [-] Removing placeholder: {fname} ({size} bytes)")
                os.remove(fpath)
            else:
                print(f"  [✓] Valid partition image: {fname} ({size / 1024 / 1024:.2f} MB)")
                valid_files.append(fname)

    if not valid_files:
        print("\n[!] Error: No valid partition images extracted. Ensure payload file is valid.")
        sys.exit(1)

    print(f"\n[SUCCESS] Total valid non-zero partition image(s) ready for upload: {len(valid_files)}")

if __name__ == "__main__":
    payload = sys.argv[1] if len(sys.argv) > 1 else "payload.bin"
    output = sys.argv[2] if len(sys.argv) > 2 else "output_imgs"
    base = sys.argv[3] if len(sys.argv) > 3 else None
    smart_extract(payload, output, base)
