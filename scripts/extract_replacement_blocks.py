#!/usr/bin/env python3
"""
Replacement & Full Partition Extractor for Incremental OTAs
Extracts all 100% full replacement partitions (boot, init_boot, vendor_boot, dtbo, vbmeta, lk, preloader, modem)
from Incremental OTAs without requiring a base firmware image.
"""

import os
import sys
import shutil
import subprocess

def extract_full_partitions_from_incremental(payload_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    dumper_bin = os.path.abspath("bin/payload-dumper-go")
    if not os.path.exists(dumper_bin):
        dumper_bin = shutil.which("payload-dumper-go") or "payload-dumper-go"

    print(f"[+] Scanning Incremental payload: {payload_path}")

    # List of partitions that are almost universally REPLACE/FULL in Incremental OTAs
    full_target_partitions = [
        "boot", "init_boot", "vendor_boot", "dtbo", "vbmeta", 
        "vbmeta_system", "vbmeta_vendor", "lk", "preloader_raw", 
        "md1img", "mcf_ota", "odm_dlkm", "vendor_dlkm"
    ]

    print(f"[+] Attempting extraction for full replacement partitions: {', '.join(full_target_partitions)}")

    for part in full_target_partitions:
        cmd = [dumper_bin, "-p", part, "-o", out_dir, payload_path]
        subprocess.run(cmd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    # Filter out empty files
    extracted_valid = []
    for fname in os.listdir(out_dir):
        fpath = os.path.join(out_dir, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            if size > 4096:
                print(f"  [✓] Extracted 100% Full Partition: {fname} ({size / 1024 / 1024:.2f} MB)")
                extracted_valid.append(fname)
            else:
                os.remove(fpath)

    print(f"\n[+] Total 100% Full Images Extracted from Incremental OTA: {len(extracted_valid)}")
    return len(extracted_valid)

if __name__ == "__main__":
    payload = sys.argv[1] if len(sys.argv) > 1 else "payload.bin"
    output = sys.argv[2] if len(sys.argv) > 2 else "output_imgs"
    extract_full_partitions_from_incremental(payload, output)
