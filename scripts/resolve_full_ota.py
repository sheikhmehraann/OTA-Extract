#!/usr/bin/env python3
"""
Automated Incremental-to-Full OTA Resolver & Prober
1. Reads remote ZIP metadata (META-INF/com/android/metadata) via HTTP Range requests in milliseconds.
2. Formulates Google Android Checkin Protobuf requests with baseline 0.
3. Automatically retrieves the FULL 7+ GB OTA ZIP URL directly from Google's servers without needing base firmware!
"""

import sys
import os
import struct
import zlib
import requests
import gzip
import re

# Add vendor path for protobuf modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = os.path.join(SCRIPT_DIR, "..", "bin", "google-ota-prober")
if not os.path.exists(VENDOR_DIR):
    VENDOR_DIR = os.path.join(SCRIPT_DIR, "..", "scratch", "transsion_prober", "vendor", "google-ota-prober")

if os.path.exists(VENDOR_DIR):
    sys.path.insert(0, VENDOR_DIR)
    sys.path.insert(0, os.path.join(VENDOR_DIR, "checkin"))
    sys.path.insert(0, os.path.join(VENDOR_DIR, "utils"))

try:
    from checkin import checkin_generator_pb2
    from utils import functions
except ImportError:
    checkin_generator_pb2 = None
    functions = None

CHECKIN_URL = "https://android.googleapis.com/checkin"

def fetch_zip_entry(url, target_entry="META-INF/com/android/metadata"):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
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
        
        cd_hdrs = dict(headers)
        cd_hdrs["Range"] = f"bytes={cd_offset}-{cd_offset + cd_size - 1}"
        cd_data = requests.get(url, headers=cd_hdrs, timeout=15).content

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

def query_google_checkin(fingerprint, device="Infinix-X6871", product="X6871-IN", model="Infinix GT 20 Pro", oem="Infinix"):
    if not checkin_generator_pb2 or not functions:
        return None

    print(f"[+] Querying Google Checkin API with baseline 0 for: {fingerprint}")
    payload = checkin_generator_pb2.AndroidCheckinRequest()
    build = checkin_generator_pb2.AndroidBuildProto()
    checkin = checkin_generator_pb2.AndroidCheckinProto()

    build.id = fingerprint
    build.timestamp = 0
    build.device = device
    build.product = product
    build.model = model
    build.manufacturer = oem
    build.brand = oem

    checkin.build.CopyFrom(build)
    checkin.roaming = "WIFI::"
    checkin.userNumber = 0
    checkin.deviceType = 2
    checkin.voiceCapable = False

    payload.imei = functions.generateImei()
    payload.id = 0
    payload.digest = functions.generateDigest()
    payload.checkin.CopyFrom(checkin)
    payload.locale = "en-US"
    payload.timeZone = "America/New_York"
    payload.version = 3
    payload.serialNumber = functions.generateSerial()
    payload.macAddr.append(functions.generateMac())
    payload.macAddrType.extend(["wifi"])
    payload.fragment = 0
    payload.userSerialNumber = 0
    payload.fetchSystemUpdates = 1

    data = gzip.compress(payload.SerializeToString())
    ua = f"Android-Checkin/2.0 ({model}; gzip)"
    headers = {
        "accept-encoding": "gzip, deflate",
        "content-encoding": "gzip",
        "content-type": "application/x-protobuffer",
        "user-agent": ua,
    }

    try:
        r = requests.post(CHECKIN_URL, data=data, headers=headers, timeout=15)
        r.raise_for_status()

        resp = checkin_generator_pb2.AndroidCheckinResponse()
        resp.ParseFromString(r.content)

        update_info = {}
        for entry in resp.setting:
            name = entry.name.decode("utf-8", errors="ignore")
            val = entry.value.decode("utf-8", errors="ignore")
            if name == "update_url":
                update_info["url"] = val
            elif name == "update_size":
                update_info["size"] = val
            elif name == "update_title":
                update_info["title"] = val

        return update_info if "url" in update_info else None
    except Exception as e:
        print(f"[!] Checkin query error: {e}")
        return None

def resolve_ota(url):
    print("==================================================")
    print(f"[+] Resolving Target OTA: {url}")
    print("==================================================")

    # 1. Fetch metadata directly from remote zip
    content = fetch_zip_entry(url, "META-INF/com/android/metadata")
    if not content:
        content = fetch_zip_entry(url, "payload_properties.txt")

    meta = {}
    if content:
        for line in content.splitlines():
            if "=" in line:
                k, v = line.strip().split("=", 1)
                meta[k.strip()] = v.strip()

    post_build = meta.get("post-build", "")
    print(f"[+] Detected Remote Post-Build: {post_build}")
    
    # 2. Extract components from post_build fingerprint
    # Format: OEM/PRODUCT/DEVICE:ANDROID_VERSION/BUILD_TAG/INCREMENTAL:TYPE/TAGS
    if post_build and checkin_generator_pb2:
        m = re.match(r"^([^/]+)/([^/]+)/([^:]+):([^/]+)/([^/]+)/([^:]+):.+$", post_build)
        if m:
            oem, product, device, android_version, build_tag, incremental = m.groups()
            
            # Formulate Baseline 0 Query to force Full OTA
            zero_fp = f"{oem}/{product}/{device}:{android_version}/{build_tag}/0:user/release-keys"
            full_res = query_google_checkin(zero_fp, device=device, product=product, model=f"{oem} {device}", oem=oem)
            
            if full_res:
                print("==================================================")
                print(f"[SUCCESS] DISCOVERED MATCHING FULL OTA PACKAGE!")
                print(f"  Title: {full_res.get('title')}")
                print(f"  Size:  {full_res.get('size')}")
                print(f"  URL:   {full_res.get('url')}")
                print("==================================================")
                return full_res.get("url")

    print("[-] Returning original OTA URL.")
    return url

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://android.googleapis.com/packages/ota-api/package/830826b787d24c4766f9564bd68afbb2e9221cc0.zip"
    resolved_url = resolve_ota(target)
    print(f"[FINAL_URL] {resolved_url}")
