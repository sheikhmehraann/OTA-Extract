#!/usr/bin/env python3
"""
Robust GoFile Uploader Script for OTA Extract Output
"""

import sys
import os
import json
import urllib.request

def upload_to_gofile(file_path):
    if not os.path.exists(file_path):
        print(f"[!] File not found: {file_path}")
        return None

    print(f"[+] Requesting active GoFile upload server...")
    try:
        req = urllib.request.Request("https://api.gofile.io/servers", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") != "ok" or not data.get("data", {}).get("servers"):
                print(f"[!] Failed to get GoFile server: {data}")
                return None
            server = data["data"]["servers"][0]["name"]
            print(f"[+] Target GoFile server: {server}")
    except Exception as e:
        print(f"[!] Error fetching GoFile servers: {e}")
        return None

    upload_url = f"https://{server}.gofile.io/contents/uploadfile"
    print(f"[+] Uploading {file_path} ({os.path.getsize(file_path) / 1024 / 1024:.2f} MB) to GoFile...")

    # Using curl for multipart upload
    import subprocess
    cmd = ["curl", "-s", "-F", f"file=@{file_path}", upload_url]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        resp_data = json.loads(res.stdout)
        if resp_data.get("status") == "ok":
            download_page = resp_data["data"]["downloadPage"]
            print("==================================================")
            print(f"[SUCCESS] GoFile Download URL: {download_page}")
            print("==================================================")
            return download_page
        else:
            print(f"[!] GoFile upload response error: {resp_data}")
    except Exception as e:
        print(f"[!] Error executing curl upload: {e}")

    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_gofile.py <file_to_upload>")
        sys.exit(1)
    upload_to_gofile(sys.argv[1])
