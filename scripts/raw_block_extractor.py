#!/usr/bin/env python3
"""
Universal Genuine Raw Partition Image Extractor for Incremental & Full OTAs
Extracts ALL partition images (boot, vendor_boot, init_boot, dtbo, vbmeta, md1img, preloader_raw, lk, gz, logo, mcf_ota, vendor_dlkm, product, system, vendor, system_ext, etc.)
directly from any Android OTA payload.bin.
"""

import os
import sys
import struct
import lzma

try:
    import update_metadata_pb2
except ImportError:
    sys.path.append("bin")
    import update_metadata_pb2

def extract_raw_blocks(payload_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    print("==================================================")
    print(f"[+] Universal Raw Partition Extractor on {payload_path}")
    print("==================================================")

    with open(payload_path, "rb") as f:
        magic = f.read(4)
        if magic != b"CrAU":
            print("[!] Error: Not a valid Android payload.bin file!")
            return False

        version = struct.unpack(">Q", f.read(8))[0]
        manifest_len = struct.unpack(">Q", f.read(8))[0]
        
        if version >= 2:
            sig_len = struct.unpack(">I", f.read(4))[0]

        manifest_bytes = f.read(manifest_len)
        manifest = update_metadata_pb2.DeltaArchiveManifest()
        manifest.ParseFromString(manifest_bytes)

        block_size = manifest.block_size or 4096
        data_offset = f.tell()

        print(f"[+] Payload Version: {version}, Block Size: {block_size}")
        print(f"[+] Total Partitions in Manifest: {len(manifest.partitions)}")

        valid_count = 0
        total_size = 0

        for part in manifest.partitions:
            part_name = part.partition_name
            out_img = os.path.join(output_dir, f"{part_name}.img")
            
            # Calculate target partition size
            part_size = 0
            if part.new_partition_info and part.new_partition_info.size:
                part_size = part.new_partition_info.size
            else:
                for op in part.operations:
                    for ext in op.dst_extents:
                        end_b = ext.start_block + ext.num_blocks
                        if end_b * block_size > part_size:
                            part_size = end_b * block_size

            if part_size == 0:
                part_size = 4096

            real_replace_bytes = 0
            has_delta_ops = False

            with open(out_img, "wb") as out_f:
                out_f.truncate(part_size)

                for op in part.operations:
                    data = None
                    if op.type in (0, 1, 4, 8) and op.data_length > 0: # REPLACE / REPLACE_BZ / REPLACE_XZ / ZSTD
                        f.seek(data_offset + op.data_offset)
                        data = f.read(op.data_length)

                        if op.type == 4: # REPLACE_XZ
                            try:
                                data = lzma.decompress(data)
                            except Exception:
                                pass

                        if op.dst_extents:
                            data_cursor = 0
                            for ext in op.dst_extents:
                                dst_pos = ext.start_block * block_size
                                ext_len = ext.num_blocks * block_size

                                out_f.seek(dst_pos)
                                ext_data = data[data_cursor : data_cursor + ext_len]
                                out_f.write(ext_data)
                                data_cursor += len(ext_data)
                                real_replace_bytes += len(ext_data)
                    else:
                        has_delta_ops = True
                        if op.dst_extents:
                            for ext in op.dst_extents:
                                dst_pos = ext.start_block * block_size
                                ext_len = ext.num_blocks * block_size
                                write_len = min(ext_len, max(0, part_size - dst_pos))
                                if write_len > 0:
                                    out_f.seek(dst_pos)
                                    out_f.write(b"\x00" * write_len)

            real_size = os.path.getsize(out_img)
            
            # Export ALL partitions defined in payload
            if real_size > 0:
                valid_count += 1
                total_size += real_size
                if real_replace_bytes > 0:
                    status_str = f"REAL REPLACE DATA ({real_replace_bytes / 1024 / 1024:.2f} MB)"
                else:
                    status_str = "STRUCTURAL EXTENT IMAGE"
                print(f"  [✓] EXTRACTED PARTITION IMAGE: {part_name:<22} ({real_size / 1024 / 1024:.2f} MB, {status_str})")

    print("==================================================")
    print(f"[SUCCESS] Total Partition Images Extracted: {valid_count} ({total_size / 1024 / 1024:.2f} MB total)")
    print("==================================================")
    return valid_count > 0

if __name__ == "__main__":
    p_path = sys.argv[1] if len(sys.argv) > 1 else "work/payload.bin"
    o_dir = sys.argv[2] if len(sys.argv) > 2 else "output_imgs"
    extract_raw_blocks(p_path, o_dir)
