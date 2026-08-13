#!/usr/bin/env python3
"""
Deep Image Inspection Script
Analyzes binary headers, magic numbers, partition signatures, and non-zero block ratios
for every .img file inside C:\\Users\\Admin\\Downloads\\ota-extract-20260813-142604.
"""

import os
import sys

def deep_inspect_folder(folder_path):
    print("==================================================")
    print(f"[+] Deep Binary Inspection on: {folder_path}")
    print("==================================================")

    if not os.path.exists(folder_path):
        print(f"[!] Path does not exist: {folder_path}")
        return

    files = sorted(os.listdir(folder_path))
    real_images = []
    fake_images = []

    for fname in files:
        fpath = os.path.join(folder_path, fname)
        if not os.path.isfile(fpath):
            continue

        size = os.path.getsize(fpath)
        with open(fpath, "rb") as f:
            header = f.read(2048)

        # Check headers & signatures
        is_boot = b"ANDROID!" in header[:64]
        is_erofs = b"\xe2\xe1\xf5\xe0" in header
        is_ext4 = b"\x53\xef" in header[1080:1082] if len(header) >= 1082 else False
        is_vbmeta = b"AVB0" in header[:64]
        is_preloader = b"MMM\x01" in header[:64] or b"EMMC_BOOT" in header[:64]

        # Calculate non-zero ratio from sample chunks
        non_zero_chunks = 0
        total_chunks = 0
        chunk_size = 65536

        with open(fpath, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                total_chunks += 1
                if any(b != 0 for b in chunk):
                    non_zero_chunks += 1

        non_zero_pct = (non_zero_chunks / total_chunks * 100) if total_chunks > 0 else 0

        # Classification
        partition_type = "UNKNOWN"
        if is_boot: partition_type = "Android Boot Header (BOOT/VENDOR_BOOT/INIT_BOOT)"
        elif is_erofs: partition_type = "EROFS Filesystem (System/Vendor/Product)"
        elif is_ext4: partition_type = "EXT4 Filesystem Image"
        elif is_vbmeta: partition_type = "AVB 2.0 VBMeta Header"
        elif is_preloader: partition_type = "MediaTek Preloader Binary"

        if non_zero_pct > 0.05 or is_boot or is_vbmeta or is_preloader or is_erofs or is_ext4:
            real_images.append((fname, size, non_zero_pct, partition_type))
            print(f"[REAL OK] {fname:<25} | Size: {size / 1024 / 1024:>8.2f} MB | Non-Zero Data: {non_zero_pct:>5.1f}% | Type: {partition_type}")
        else:
            fake_images.append((fname, size, non_zero_pct))
            print(f"[FAKE 0x0] {fname:<25} | Size: {size / 1024 / 1024:>8.2f} MB | Non-Zero Data: {non_zero_pct:>5.1f}% | (Delta Patch required Base ROM)")

    print("==================================================")
    print(f"[SUMMARY] Total Files Inspected: {len(files)}")
    print(f"[SUMMARY] REAL Binary Partition Images: {len(real_images)}")
    print(f"[SUMMARY] FAKE 0-Byte Delta Placeholders: {len(fake_images)}")
    print("==================================================")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Admin\Downloads\ota-extract-20260813-142604"
    deep_inspect_folder(target)
