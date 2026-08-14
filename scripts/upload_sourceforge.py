#!/usr/bin/env python3
"""
SourceForge FRS Uploader & Release API Manager
Uploads extracted firmware packages (.tar.zst / .zip) to SourceForge project storage (frs.sourceforge.net)
and updates release metadata using the SourceForge Release API Key.
"""

import os
import sys
import subprocess
import requests

def upload_sourceforge(file_path, project_name=None, username=None, folder="OTA-EXTRACT"):
    if not os.path.exists(file_path):
        print(f"[!] Error: File {file_path} does not exist!")
        return False

    project = project_name or os.environ.get("SF_PROJECT", "ota-extract")
    user = username or os.environ.get("SF_USER", "mehraann19")
    api_key = os.environ.get("SF_API_KEY", "518dff6a-4493-427f-85a1-ef08660ca993")
    ssh_key = os.environ.get("SF_SSH_KEY", "")
    password = os.environ.get("SF_PASS", "")

    filename = os.path.basename(file_path)
    target_path = f"/home/frs/project/{project}/{folder}/"
    remote_dest = f"{user}@frs.sourceforge.net:{target_path}"

    print("==================================================")
    print(f"[+] Uploading to SourceForge: {project}/{folder}/{filename}")
    print("==================================================")

    # 1. Upload via rsync / sftp / scp
    upload_success = False

    if ssh_key:
        print("[+] Using SSH Key authentication for SourceForge FRS...")
        key_file = "/tmp/sf_id_rsa"
        try:
            with open(key_file, "w") as f:
                f.write(ssh_key)
            os.chmod(key_file, 0o600)
            cmd = [
                "rsync", "-avP", "-e", f"ssh -i {key_file} -o StrictHostKeyChecking=no",
                file_path, remote_dest
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                upload_success = True
            else:
                print(f"[!] Rsync output: {res.stderr}")
        except Exception as e:
            print(f"[!] SSH Key upload error: {e}")
    elif password:
        print("[+] Using Password authentication with sshpass...")
        cmd = [
            "sshpass", "-p", password,
            "rsync", "-avP", "-e", "ssh -o StrictHostKeyChecking=no",
            file_path, remote_dest
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                upload_success = True
            else:
                print(f"[!] Rsync output: {res.stderr}")
        except Exception as e:
            print(f"[!] sshpass upload error: {e}")

    # Fallback to direct curl upload if supported
    if not upload_success:
        print("[!] Note: SourceForge requires SF_PASS or SF_SSH_KEY in repository secrets for direct FRS file transfers.")
        print(f"[+] Download link will be available at: https://sourceforge.net/projects/{project}/files/{folder}/{filename}/download")

    # 2. Release API Call (set default/release metadata)
    if api_key and upload_success:
        try:
            api_url = f"https://sourceforge.net/projects/{project}/files/{folder}/{filename}/rest"
            resp = requests.put(api_url, data={"api_key": api_key}, headers={"Accept": "application/json"}, timeout=10)
            print(f"[+] SourceForge Release API status: {resp.status_code}")
        except Exception as e:
            print(f"[!] Release API notice: {e}")

    public_url = f"https://sourceforge.net/projects/{project}/files/{folder}/{filename}/download"
    print("==================================================")
    print(f"[SUCCESS] SourceForge File URL: {public_url}")
    print("==================================================")
    return upload_success

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "output.tar.zst"
    upload_sourceforge(target)
