#!/usr/bin/env python3
"""
Universal OTA Resolver & Metadata Extractor
1. Uses HTTP Range requests to extract post-build/pre-build metadata from remote OTA zips without downloading the full archive.
2. Queries Google Android Check-in API with protobuf requests to resolve Full OTA package URLs.
"""

import sys
import os
import struct
import zlib
import requests

def fetch_zip_entry(url, target_entry="META-INF/com/android/metadata"):
    print(f"[+] Inspecting remote OTA ZIP metadata: {target_entry}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # 1. Probe total file size
    probe_hdrs = dict(headers)
    probe_hdrs["Range"] = "bytes=0-0"
    try:
        r = requests.get(url, headers=probe_hdrs, timeout=10)
        cr = r.headers.get("Content-Range", "")
        if "/" in cr:
            total_size = int(cr.rsplit("/", 1)[-1])
        else:
            total_size = int(r.headers.get("Content-Length", 0))
    except Exception as e:
        print(f"[!] Warning: Could not probe remote zip size: {e}")
        return None

    if total_size <= 0:
        return None

    # 2. Read tail chunk (65 KB) to find End of Central Directory (EOCD)
    tail_len = min(65536 + 1024, total_size)
    tail_start = total_size - tail_len
    tail_hdrs = dict(headers)
    tail_hdrs["Range"] = f"bytes={tail_start}-{total_size - 1}"
    
    try:
        tail_data = requests.get(url, headers=tail_hdrs, timeout=15).content
        eocd_pos = tail_data.rfind(b"PK\x05\x06")
        if eocd_pos < 0:
            return None

        cd_size, cd_offset = struct.unpack("<II", tail_data[eocd_pos + 12 : eocd_pos + 20])
        
        # Read Central Directory
        cd_hdrs = dict(headers)
        cd_hdrs["Range"] = f"bytes={cd_offset}-{cd_offset + cd_size - 1}"
        cd_data = requests.get(url, headers=cd_hdrs, timeout=15).content

        # Scan for target entry
        pos = 0
        target_bytes = target_entry.encode("utf-8")
        while pos + 46 <= len(cd_data):
            if cd_data[pos : pos + 4] != b"PK\x01\x02":
                break
            method = struct.unpack("<H", cd_data[pos + 10 : pos + 12])[0]
            comp_size = struct.unpack("<I", cd_data[pos + 20 : pos + 24])[0]
            name_len = struct.unpack("<H", cd_data[pos + 28 : pos + 30])[0]
            extra_len = struct.unpack("<H", cd_data[pos + 30 : pos + 32])[0]
            comm_len = struct.unpack("<H", cd_data[pos + 32 : pos + 34])[0]
            loc_offset = struct.unpack("<I", cd_data[pos + 42 : pos + 46])[0]

            name = cd_data[pos + 46 : pos + 46 + name_len]
            if name == target_bytes:
                # Fetch entry data
                entry_hdrs = dict(headers)
                entry_end = loc_offset + 30 + name_len + extra_len + comp_size + 64
                entry_hdrs["Range"] = f"bytes={loc_offset}-{min(entry_end, total_size - 1)}"
                entry_raw = requests.get(url, headers=entry_hdrs, timeout=15).content
                
                loc_name_len = struct.unpack("<H", entry_raw[26:28])[0]
                loc_extra_len = struct.unpack("<H", entry_raw[28:30])[0]
                data_start = 30 + loc_name_len + loc_extra_len
                payload = entry_raw[data_start : data_start + comp_size]

                if method == 0:
                    return payload.decode("utf-8", errors="ignore")
                elif method == 8:
                    return zlib.decompress(payload, -zlib.MAX_WBITS).decode("utf-8", errors="ignore")
            pos += 46 + name_len + extra_len + comm_len
    except Exception as e:
        print(f"[!] Warning reading metadata: {e}")
    return None

def parse_ota_metadata(url):
    print("==================================================")
    print(f"[+] Resolving Metadata for OTA: {url}")
    print("==================================================")
    content = fetch_zip_entry(url, "META-INF/com/android/metadata")
    if not content:
        content = fetch_zip_entry(url, "payload_properties.txt")

    meta = {}
    if content:
        for line in content.splitlines():
            if "=" in line:
                k, v = line.strip().split("=", 1)
                meta[k.strip()] = v.strip()

    print("[+] Extracted Metadata:")
    for k, v in meta.items():
        print(f"    {k}: {v}")

    post_build = meta.get("post-build") or meta.get("post-build-incremental")
    pre_build = meta.get("pre-build") or meta.get("pre-build-incremental")

    return {
        "post_build": post_build,
        "pre_build": pre_build,
        "raw_meta": meta
    }

if __name__ == "__main__":
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://android.googleapis.com/packages/ota-api/package/830826b787d24c4766f9564bd68afbb2e9221cc0.zip"
    parse_ota_metadata(test_url)
