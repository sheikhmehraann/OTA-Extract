#!/usr/bin/env python3
"""
GitHub Actions Workflow Run Monitor & Log Extractor
Monitors a GitHub Actions run ID until completion and prints the GoFile download URL.
"""

import sys
import time
import subprocess

def monitor(run_id="31713724266", repo="sheikhmehraann/OTA-Extract"):
    print(f"[+] Monitoring GitHub Run ID: {run_id} on {repo}...")
    
    while True:
        try:
            cmd = ["gh", "run", "view", run_id, "--repo", repo]
            res = subprocess.run(cmd, capture_output=True, text=True)
            output = res.stdout
            
            if "completed" in output:
                print(f"[+] Run {run_id} completed!")
                log_cmd = ["gh", "run", "view", run_id, "--repo", repo, "--log"]
                log_res = subprocess.run(log_cmd, capture_output=True, text=True)
                
                for line in log_res.stdout.splitlines():
                    if "gofile.io" in line or "GENUINE REAL PARTITION IMAGE" in line or "SUCCESS" in line:
                        print(line)
                break
            else:
                print(f"[*] Run status: in_progress... waiting 10s")
                time.sleep(10)
        except Exception as e:
            print(f"[!] Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "31713724266"
    monitor(rid)
