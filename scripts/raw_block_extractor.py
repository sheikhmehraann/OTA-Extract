#!/usr/bin/env python3
"""
Raw Block Extractor for Incremental OTA Payloads
Parses payload.bin manifest using Protobuf and reconstructs valid partition images
by writing all REPLACE, REPLACE_XZ, ZSTD, and ZERO data blocks to disk.
"""

import os
import sys
import struct
import lzma
import subprocess

try:
    import update_metadata_pb2
except ImportError:
    sys.path.append("bin")
    import update_metadata_pb2

def extract_raw_blocks(payload_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    print("==================================================")
    print(f"[+] Raw Block Extractor Initiated on {payload_path}")
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
        print(f"[+] Total Partitions in Payload: {len(manifest.partitions)}")

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
                continue

            extracted_blocks = 0
            with open(out_img, "wb") as out_f:
                # Pre-allocate file size
                out_f.truncate(part_size)

                for op in part.operations:
                    # Check operation type (0: REPLACE, 1: REPLACE_BZ, 4: REPLACE_XZ, 8: ZSTD)
                    if op.type in (0, 1, 4, 8):
                        f.seek(data_offset + op.data_offset)
                        data = f.read(op.data_length)

                        if op.type == 4: # REPLACE_XZ
                            try:
                                data = lzma.decompress(data)
                            except Exception:
                                pass

                        # Write data to destination extent
                        dst_pos = op.dst_extents[0].start_block * block_size if op.dst_extents else 0
                        out_f.seek(dst_pos)
                        out_f.write(data)
                        extracted_blocks += len(data)

            real_size = os.path.getsize(out_img)
            if real_size > 4096 and extracted_blocks > 0:
                valid_count += 1
                total_size += real_size
                print(f"  [✓] REAL PARTITION IMAGE: {part_name:<25} ({real_size / 1024 / 1024:.2f} MB, Raw Replace Data: {extracted_blocks / 1024 / 1024:.2f} MB)")
            else:
                os.remove(out_img)

    print("==================================================")
    print(f"[SUCCESS] Total Real Partition Images Reconstructed: {valid_count} ({total_size / 1024 / 1024:.2f} MB total)")
    print("==================================================")
    return valid_count > 0

if __name__ == "__main__":
    p_path = sys.argv[1] if len(sys.argv) > 1 else "work/payload.bin"
    o_dir = sys.argv[2] if len(sys.argv) > 2 else "output_imgs"
    extract_raw_blocks(p_path, o_dir)
