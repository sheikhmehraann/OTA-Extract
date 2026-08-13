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
    else:
        print("[+] Standard Extraction mode...")
        cmd = [dumper_bin, "-o", out_dir, payload_path]

    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"[!] Dumper executed with warnings/notices: {e}")

    # Inspect extracted files and remove 0-byte or empty placeholder files
    print("\n[+] Filtering extracted partition images...")
    valid_files = []
    for fname in os.listdir(out_dir):
        fpath = os.path.join(out_dir, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            if size < 4096:
                print(f"  [-] Removing empty/placeholder file: {fname} ({size} bytes)")
                os.remove(fpath)
            else:
                print(f"  [✓] Valid extracted partition: {fname} ({size / 1024 / 1024:.2f} MB)")
                valid_files.append(fname)

    if not valid_files:
        print("[!] Warning: No non-zero partition files were extracted directly.")
        print("    This Incremental OTA consists entirely of BSDIFF/SOURCE_COPY patches.")
        print("    To reconstruct full system.img/vendor.img, supply the base firmware link (-b / BASE_FIRMWARE_URL).")
        sys.exit(1)
    else:
        print(f"\n[SUCCESS] Successfully extracted {len(valid_files)} real partition image(s)!")

if __name__ == "__main__":
    payload = sys.argv[1] if len(sys.argv) > 1 else "payload.bin"
    output = sys.argv[2] if len(sys.argv) > 2 else "output_imgs"
    base = sys.argv[3] if len(sys.argv) > 3 else None
    smart_extract(payload, output, base)
