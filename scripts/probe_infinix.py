#!/usr/bin/env python3
"""
Infinix GT 20 Pro (X6871) OTA Probe & Extractor Link Helper
Uses Transsion OTA API logic to query update packages for MT6896/MT6895 platform.
"""

import sys
import json
import urllib.request

TRANSSION_API_URL = "https://aotu-ota.transsion.com/otacheck/checkUpdate"

def probe_infinix_ota(fingerprint, model="X6871", version="X6871-V0.0.1"):
    print(f"[+] Probing Transsion OTA servers for Infinix {model} ({fingerprint})...")
    payload = {
        "params": {
            "model": model,
            "version": version,
            "fingerprint": fingerprint
        }
    }
    
    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 14; X6871 Build/UP1A.231005.007)",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(TRANSSION_API_URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("[+] Response received from Transsion OTA server:")
            print(json.dumps(data, indent=2))
            return data
    except Exception as e:
        print(f"[!] Error probing Transsion server: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python probe_infinix.py <build_fingerprint_or_version>")
        print("Example: python probe_infinix.py X6871-V1200")
        sys.exit(0)
    
    ver = sys.argv[1]
    probe_infinix_ota(fingerprint=ver, version=ver)
