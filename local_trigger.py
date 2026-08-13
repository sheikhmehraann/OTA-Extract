#!/usr/bin/env python3
"""
OTA Extract CLI Trigger Tool
Fires the GitHub Actions cloud extraction workflow remotely using gh CLI.
"""

import sys
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description="Trigger GitHub Actions Android OTA Extraction")
    parser.add_argument("-u", "--url", required=True, help="Direct download URL to OTA ZIP or payload.bin")
    parser.add_argument("-t", "--type", choices=["FULL", "INCREMENTAL"], default="FULL", help="OTA type (FULL or INCREMENTAL)")
    parser.add_argument("-b", "--base", default="", help="Base Firmware URL (Optional for INCREMENTAL)")
    parser.add_argument("-p", "--partitions", default="all", help="Partitions to extract (e.g. boot,init_boot or all)")
    parser.add_argument("-dest", "--target", choices=["release", "pixeldrain", "gofile", "artifacts"], default="release", help="Upload destination")
    
    args = parser.parse_args()

    print(f"[+] Triggering GitHub Action Workflow...")
    print(f"    OTA URL: {args.url}")
    print(f"    Type: {args.type}")
    if args.base:
        print(f"    Base Firmware URL: {args.base}")
    print(f"    Partitions: {args.partitions}")
    print(f"    Upload Target: {args.target}")

    cmd = [
        "gh", "workflow", "run", "ota_extract.yml",
        "-f", f"ota_url={args.url}",
        "-f", f"ota_type={args.type}",
        "-f", f"base_firmware_url={args.base}",
        "-f", f"partitions={args.partitions}",
        "-f", f"upload_target={args.target}"
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("[SUCCESS] Workflow successfully triggered!")
        print(res.stdout)
        print("[+] Check workflow progress using: gh run list --workflow=ota_extract.yml")
    except FileNotFoundError:
        print("[!] GitHub CLI ('gh') is not installed or not in PATH.")
    except subprocess.CalledProcessError as e:
        print(f"[!] Error triggering workflow: {e.stderr}")

if __name__ == "__main__":
    main()
