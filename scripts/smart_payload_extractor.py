#!/usr/bin/env python3
"""
Smart Android OTA Payload Extractor & Reconstructor
Extracts valid partition images, filters out empty delta placeholders,
and applies incremental diff patching when base images are supplied.
"""

import os
import sys
import shutil
import subprocess
from extract_replacement_blocks import extract_full_partitions_from_incremental

def smart_extract(payload_path, out_dir, old_dir=None):
    os.makedirs(out_dir, exist_ok=True)
    dumper_bin = os.path.abspath("bin/payload-dumper-go")
    
    if not os.path.exists(dumper_bin):
        dumper_bin = shutil.which("payload-dumper-go") or "payload-dumper-go"

    print(f"[+] Using dumper binary: {dumper_bin}")
    print(f"[+] Payload target: {payload_path}")

    if old_dir and os.path.exists(old_dir):
        print(f"[+] Base images directory provided: {old_dir}. Running Incremental Diff Patching...")
        cmd = [dumper_bin, "extract-diff", payload_path, "--old", old_dir, "-o", out_dir]
        subprocess.run(cmd, check=False)
    else:
        print("[+] Running Standard Extraction...")
        cmd = [dumper_bin, "-o", out_dir, payload_path]
        subprocess.run(cmd, check=False)

    # Inspect extracted files and remove 0-byte or empty placeholder files
    print("\n[+] Filtering extracted partition images...")
    valid_files = []
    for fname in os.listdir(out_dir):
        fpath = os.path.join(out_dir, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            if size < 4096:
                os.remove(fpath)
            else:
                print(f"  [✓] Valid extracted partition: {fname} ({size / 1024 / 1024:.2f} MB)")
                valid_files.append(fname)

    if not valid_files:
        print("\n[!] Standard extraction yielded BSDIFF placeholders for system/vendor.")
        print("[+] Falling back to Replacement Partition Extraction (boot, init_boot, vendor_boot, dtbo, vbmeta, modem)...")
        count = extract_full_partitions_from_incremental(payload_path, out_dir)
        if count > 0:
            for fname in os.listdir(out_dir):
                fpath = os.path.join(out_dir, fname)
                if os.path.isfile(fpath) and os.path.getsize(fpath) > 4096:
                    valid_files.append(fname)

    print(f"\n[SUCCESS] Total valid non-zero partition image(s) ready for package: {len(valid_files)}")

if __name__ == "__main__":
    payload = sys.argv[1] if len(sys.argv) > 1 else "payload.bin"
    output = sys.argv[2] if len(sys.argv) > 2 else "output_imgs"
    base = sys.argv[3] if len(sys.argv) > 3 else None
    smart_extract(payload, output, base)
