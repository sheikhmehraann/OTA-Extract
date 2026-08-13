#!/usr/bin/env python3
"""
Transsion Auto Base & Incremental Payload Extractor Engine
Queries Transsion update API for Infinix X6871 to auto-resolve matching base firmware
or extracts full replacement images directly.
"""

import os
import sys
import json
import urllib.request
import subprocess

TRANSSION_API_URL = "https://otacheck.transsion.com/otacheck/checkUpdate"

def fetch_full_ota_url(build_version="X6871-V0.0.1"):
    print(f"[+] Querying Transsion OTA API for Full ROM Link (Version: {build_version})...")
    payload = {
        "params": {
            "version": build_version,
            "device": "X6871",
            "brand": "Infinix",
            "module": "X6871-user",
            "type": "2"
        }
    }
    headers = {"Content-Type": "application/json", "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 14; Infinix X6871 Build/UP1A.231005.007)"}
    
    try:
        req = urllib.request.Request(TRANSSION_API_URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"[+] Transsion API Response: {data}")
            url = data.get("data", {}).get("downloadUrl") or data.get("downloadUrl")
            if url:
                print(f"[SUCCESS] Found Transsion Full OTA URL: {url}")
                return url
    except Exception as e:
        print(f"[!] Transsion API Query Exception: {e}")
    return None

if __name__ == "__main__":
    ver = sys.argv[1] if len(sys.argv) > 1 else "X6871-V0.0.1"
    fetch_full_ota_url(ver)
