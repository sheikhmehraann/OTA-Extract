#!/usr/bin/env python3
import urllib.request
import zipfile
import io
import re

URL = "https://android.googleapis.com/packages/ota-api/package/830826b787d24c4766f9564bd68afbb2e9221cc0.zip"

print(f"[+] Connecting to: {URL}")
req = urllib.request.Request(URL, method='HEAD')
try:
    with urllib.request.urlopen(req) as resp:
        content_length = int(resp.headers.get('Content-Length', 0))
        print(f"[+] Total OTA Package Size: {content_length} bytes ({content_length / 1024 / 1024:.2f} MB)")
except Exception as e:
    print(f"[!] HEAD request failed: {e}")
    content_length = 0

# Fetch the tail of the zip (where central directory lives)
tail_size = min(10 * 1024 * 1024, content_length) if content_length > 0 else 10 * 1024 * 1024
req_tail = urllib.request.Request(URL, headers={'Range': f'bytes={content_length - tail_size}-{content_length - 1}'})

try:
    print(f"[+] Fetching last {tail_size / 1024 / 1024:.2f} MB of ZIP central directory...")
    with urllib.request.urlopen(req_tail) as resp:
        tail_data = resp.read()
        print(f"[+] Received tail data ({len(tail_data)} bytes)")
        
        # Search for payload_properties.txt or metadata in raw bytes if ZipFile fails due to partial bytes
        props_match = re.search(b"FILE_HASH=.*", tail_data)
        if props_match:
            print("[+] Found payload properties in tail:")
            print(props_match.group(0).decode('utf-8', errors='ignore')[:500])
except Exception as e:
    print(f"[!] Error inspecting tail: {e}")
