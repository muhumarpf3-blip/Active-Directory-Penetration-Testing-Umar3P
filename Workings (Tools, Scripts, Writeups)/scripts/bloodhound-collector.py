#!/usr/bin/env python3
"""
bloodhound-collector.py — BloodHound CE Collection Wrapper
Author: Vimal Raj M | github.com/vimalraj-sec
Purpose: Streamlined BloodHound data collection with auto output naming and import instructions

Usage:
  python3 bloodhound-collector.py -d corp.local --dc 10.10.10.100 -u jsmith -p Password123!
  python3 bloodhound-collector.py -d corp.local --dc 10.10.10.100 -u jsmith -p Password123! -c DCOnly

Requires:
  sudo apt install netexec  OR  pip install bloodhound --break-system-packages
  BloodHound CE running: sudo docker-compose up -d

⚠️ For authorized penetration testing only.
"""

import argparse
import subprocess
import sys
import os
import time
from datetime import datetime


def start_bloodhound_check():
    """Check if BloodHound CE is running."""
    result = subprocess.run(['sudo', 'docker', 'ps'], capture_output=True, text=True)
    if 'bloodhound' in result.stdout.lower():
        print("[+] BloodHound CE is running → http://localhost:8080")
    else:
        print("[!] BloodHound CE not detected.")
        print("[*] Start with: cd /home/kali/Arsenal/ActiveDirectory/BloodHoundCE && sudo docker-compose up -d")
        print("[*] Get password: sudo docker logs bloodhoundce-bloodhound-1 | grep -i pass")


def collect_nxc(args, output_dir):
    """Collect BloodHound data via netexec."""
    print(f"\n[*] Collector  : netexec (nxc ldap --bloodhound)")
    print(f"[*] Collection : {args.collection}")
    print(f"[*] Output dir : {output_dir}")
    print(f"[*] Started at : {time.strftime('%H:%M:%S')}\n")

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        'sudo', 'nxc', 'ldap', args.dc,
        '-u', args.username,
        '-p', args.password,
        '--bloodhound',
        '--collection', args.collection,
        '--dns-server', args.dc,
    ]

    original_dir = os.getcwd()
    os.chdir(output_dir)
    result = subprocess.run(cmd, text=True)
    os.chdir(original_dir)

    # Find output zip
    zips = [f for f in os.listdir(output_dir) if f.endswith('.zip')]
    if zips:
        latest = max(zips, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
        full_path = os.path.join(output_dir, latest)
        size = os.path.getsize(full_path)
        print(f"\n[+] Collection complete at {time.strftime('%H:%M:%S')}")
        print(f"[+] Output     : {full_path} ({size/1024:.0f} KB)")
        return full_path
    else:
        print(f"[-] No zip found in {output_dir}. Collection may have failed.")
        return None


def collect_bloodhound_python(args, output_dir):
    """Collect BloodHound data via bloodhound-python."""
    print(f"\n[*] Collector  : bloodhound-python")
    print(f"[*] Collection : {args.collection}")
    print(f"[*] Output dir : {output_dir}")
    print(f"[*] Started at : {time.strftime('%H:%M:%S')}\n")

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        'bloodhound-python',
        '-d', args.domain,
        '-ns', args.dc,
        '-u', args.username,
        '-p', args.password,
        '-c', args.collection,
        '--zip',
        '--dns-tcp',
    ]

    original_dir = os.getcwd()
    os.chdir(output_dir)
    result = subprocess.run(cmd, text=True)
    os.chdir(original_dir)

    zips = [f for f in os.listdir(output_dir) if f.endswith('.zip')]
    if zips:
        latest = max(zips, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
        full_path = os.path.join(output_dir, latest)
        size = os.path.getsize(full_path)
        print(f"\n[+] Collection complete at {time.strftime('%H:%M:%S')}")
        print(f"[+] Output     : {full_path} ({size/1024:.0f} KB)")
        return full_path
    return None


def print_import_steps(zip_path):
    """Print BloodHound CE import instructions."""
    print(f"""
{'='*60}
  BloodHound CE — Import Instructions
{'='*60}

1. Open browser: http://localhost:8080
   Login: admin / (check: sudo docker logs bloodhoundce-bloodhound-1 | grep -i pass)

2. Click "Upload Files" → select:
   {zip_path}

3. Wait for ingestion to complete.

4. Mark owned nodes:
   Right-click your compromised account → "Mark as Owned"

5. Run these queries:
   → Shortest Paths to Domain Admins from Owned
   → Find Principals with DCSync Rights
   → Find AS-REP Roastable Users (DontReqPreAuth)
   → Find Kerberoastable Users
   → Computers where Domain Users are Local Admin

6. Icon reference:
   ORANGE = OU  |  PURPLE = GPO Policy
{'='*60}
""")


def main():
    parser = argparse.ArgumentParser(
        description='BloodHound CE Collection Wrapper'
    )
    parser.add_argument('-d', '--domain', required=True,
                        help='Domain (e.g. corp.local)')
    parser.add_argument('--dc', required=True,
                        help='DC IP address')
    parser.add_argument('-u', '--username', required=True,
                        help='Username with domain credentials')
    parser.add_argument('-p', '--password', required=True,
                        help='Password')
    parser.add_argument('-c', '--collection', default='All',
                        choices=['All', 'DCOnly', 'Session', 'Default'],
                        help='Collection method (default: All)')
    parser.add_argument('-o', '--output', default='enum/bloodhound',
                        help='Output base directory (default: enum/bloodhound)')
    parser.add_argument('--tool', choices=['nxc', 'bloodhound-python', 'auto'],
                        default='auto',
                        help='Collection tool (default: auto — prefers nxc)')
    args = parser.parse_args()

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output_dir = f"{args.output}/{args.domain}-{timestamp}"

    print(f"\n{'='*60}")
    print(f"  BloodHound CE Collection")
    print(f"{'='*60}")
    print(f"  Domain     : {args.domain}")
    print(f"  DC IP      : {args.dc}")
    print(f"  User       : {args.domain}\\{args.username}")
    print(f"  Collection : {args.collection}")
    print(f"  Output     : {output_dir}")
    print(f"{'='*60}")

    start_bloodhound_check()

    zip_path = None

    if args.tool == 'auto' or args.tool == 'nxc':
        nxc_check = subprocess.run(['which', 'nxc'], capture_output=True)
        if nxc_check.returncode == 0:
            zip_path = collect_nxc(args, output_dir)
        elif args.tool == 'nxc':
            print("[!] nxc not found. Install: sudo apt install netexec")
            sys.exit(1)

    if zip_path is None and (args.tool == 'auto' or args.tool == 'bloodhound-python'):
        bp_check = subprocess.run(['which', 'bloodhound-python'], capture_output=True)
        if bp_check.returncode == 0:
            zip_path = collect_bloodhound_python(args, output_dir)
        else:
            print("[!] Neither nxc nor bloodhound-python found.")
            print("[*] Manual: sudo nxc ldap $ip -u USER -p PASS --bloodhound --collection All --dns-server $ip")
            sys.exit(1)

    if zip_path and os.path.exists(zip_path):
        print_import_steps(zip_path)
    else:
        print("\n[-] Collection failed. Manual fallback:")
        print(f"    sudo nxc ldap {args.dc} -u {args.username} -p PASS --bloodhound --collection All --dns-server {args.dc}")


if __name__ == '__main__':
    main()
