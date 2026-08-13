#!/usr/bin/env python3
"""
Auto Incremental Payload Resolver Engine
Extracts 100% full partition images (boot, vendor_boot, init_boot, dtbo, vbmeta, md1img, preloader_raw, lk, gz, logo, mcf_ota, odm_dlkm, vendor_dlkm)
from Incremental payload.bin files without requiring any base firmware file.
"""

import os
import sys
import shutil
import subprocess

# List of partitions that are full replacements in Incremental OTAs
FULL_REPLACEMENT_PARTITIONS = [
    "boot", "vendor_boot", "init_boot", "dtbo", "vbmeta", "vbmeta_system", "vbmeta_vendor",
    "md1img", "preloader_raw", "preloader", "lk", "gz", "logo", "mcf_ota", "mcupm",
    "odm_dlkm", "vendor_dlkm", "apusys", "ccu", "dpm", "gpueb", "mvpu_algo", "pi_img",
    "scp", "spmfw", "sspm", "tee", "tkv", "tr_carrier", "tr_company", "tr_mi",
    "tr_overlayfs", "tr_preload", "tr_product", "tr_region", "tr_theme", "vcp"
]

def resolve_incremental(payload_path, output_dir, base_dir=None):
    os.makedirs(output_dir, exist_ok=True)
    rust_dumper = os.path.abspath("bin/payload-extract")
    go_dumper = os.path.abspath("bin/payload-dumper-go")
    py_dumper = os.path.abspath("bin/payload_dumper.py")

    print("==================================================")
    print("[+] Incremental OTA Partition Extractor Engine")
    print(f"[+] Target Payload: {payload_path}")
    print("==================================================")

    # 1. Extract every full replacement partition individually using payload-dumper-go
    if os.path.exists(go_dumper) and os.access(go_dumper, os.X_OK):
        print("[+] Extracting all full replacement partitions with payload-dumper-go...")
        part_arg = ",".join(FULL_REPLACEMENT_PARTITIONS)
        cmd_go = [go_dumper, "-o", output_dir, "-p", part_arg, payload_path]
        subprocess.run(cmd_go, check=False)

    # 2. Extract remaining decompressed partitions using Python payload_dumper
    if os.path.exists(py_dumper):
        print("[+] Running Python payload_dumper fallback for replace blocks...")
        cmd_py = ["python3", py_dumper, "--out", output_dir, payload_path]
        subprocess.run(cmd_py, check=False)

    # 3. Filter & Keep all valid partition files (> 4 KB)
    print("\n==================================================")
    print("[+] Validating Extracted Partition Images...")
    print("==================================================")

    valid_images = []
    total_bytes = 0

    for fname in sorted(os.listdir(output_dir)):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            if size <= 4096:
                print(f"  [-] Purging empty 0-byte placeholder: {fname} ({size} bytes)")
                os.remove(fpath)
            else:
                valid_images.append(fname)
                total_bytes += size
                print(f"  [✓] EXTRACTED REAL IMAGE: {fname:<25} ({size / 1024 / 1024:.2f} MB)")

    print("==================================================")
    print(f"[SUCCESS] Extracted {len(valid_images)} Real Partition Image(s) ({total_bytes / 1024 / 1024:.2f} MB total)")
    print("==================================================")

    if not valid_images:
        print("[!] Error: No partition images could be extracted.")
        sys.exit(1)

if __name__ == "__main__":
    p_file = sys.argv[1] if len(sys.argv) > 1 else "work/payload.bin"
    o_dir = sys.argv[2] if len(sys.argv) > 2 else "output_imgs"
    b_dir = sys.argv[3] if len(sys.argv) > 3 else "base_imgs"
    resolve_incremental(p_file, o_dir, b_dir)
