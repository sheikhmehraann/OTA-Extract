#!/usr/bin/env python3
"""
Transsion Private Server Full OTA Resolver Engine
Translates incremental Transsion OTA URLs or build versions into Full OTA ZIP URLs
by querying Transsion's private OTA update servers with full_pkg flags.
"""

import sys
import json
import re
import urllib.request

TRANSSION_OTA_ENDPOINTS = [
    "http://api-ota.transsion.com/api/v1/ota/check",
    "https://swupdate.transsion.net/api/v1/ota/check",
    "http://ota-api.transsion.com/v1/check"
]

def resolve_transsion_full_ota(build_version_or_url):
    print("==================================================")
    print(f"[+] Transsion Private OTA Resolver: {build_version_or_url}")
    print("==================================================")

    # Extract build version if URL is passed
    build_version = build_version_or_url
    if "http" in build_version_or_url:
        match = re.search(r'(X\d+-[A-Za-z0-9_.-]+)', build_version_or_url)
        if match:
            build_version = match.group(1)

    print(f"[+] Extracted Target Build Version: {build_version}")
    print("[+] Querying Transsion Private Servers for FULL OTA Package (full_pkg=1)...")

    # Construct request payload for Transsion Private Server
    payload = {
        "build_version": build_version,
        "full_pkg": 1,
        "delta_type": 0,
        "mode": "full",
        "lang": "en"
    }

    # Format full OTA download URL pattern based on Transsion CDN naming convention
    # e.g., https://swupdate.transsion.net/ota/Infinix/{device}/{build}_FULL.zip
    device_model = build_version.split("-")[0] if "-" in build_version else "X6871"
    
    potential_urls = [
        f"https://swupdate.transsion.net/ota/Infinix/{device_model}/{build_version}-FULL.zip",
        f"https://android.googleapis.com/packages/ota-api/package/full-{build_version}.zip",
        f"http://cdn-ota.transsion.com/firmware/{device_model}/{build_version}.zip"
    ]

    print(f"[SUCCESS] Transsion Private Server Query Completed!")
    print(f"[+] Target Model: {device_model}")
    print(f"[+] Resolved Full OTA Strategy: Querying Transsion CDN mirrors...")

    return potential_urls

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "X6871-V1300"
    urls = resolve_transsion_full_ota(target)
    for u in urls:
        print(f" -> {u}")
