# 🖥️ Local AD Lab Setup — OSCP.EXAM

Personal lab built for Active Directory penetration testing practice.  
Mirrors a real corporate environment — DC, two Windows 11 workstations, intentional misconfigurations, live attack targets.

---

## Lab Architecture

```
┌─────────────────────────────────────────────────────────┐
│               VirtualBox Host-Only Network               │
│                    192.168.56.0/24                       │
│                                                          │
│  ┌────────────────┐   ┌──────────────┐  ┌────────────┐  │
│  │  Kali Linux    │   │  DC01        │  │   MS01     │  │
│  │  Attacker      │   │  Windows     │  │  Windows   │  │
│  │  .10           │   │  Server 2025 │  │  11        │  │
│  │                │   │  .100        │  │  .101      │  │
│  └────────────────┘   └──────────────┘  └────────────┘  │
│                                                          │
│                        ┌──────────────────────────────┐  │
│                        │  MS02                        │  │
│                        │  Windows 11                  │  │
│                        │  .102                        │  │
│                        └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Lab Configuration

### Machines

| Hostname | OS | Role | IP |
|----------|----|------|----|
| DC01 | Windows Server 2025 | Domain Controller | 192.168.56.100 |
| MS01 | Windows 11 | Domain Workstation | 192.168.56.101 |
| MS02 | Windows 11 | Domain Workstation | 192.168.56.102 |
| Kali | Kali Linux | Attacker | 192.168.56.10 |

### Domain

```
Domain Name   : OSCP.EXAM
Server Name   : DC01
NetBIOS Name  : OSCP
```

---

## Credentials Reference

### Machine Local Accounts

| Machine | Username | Password |
|---------|----------|----------|
| MS01 | CLIENT01 | Password1! |
| MS02 | CLIENT02 | Password2! |
| MS01 | Administrator | Password1! |
| MS02 | Administrator | Password2! |

### Domain Users

| Username | Password | Notes |
|----------|----------|-------|
| clark.kent | Password1 | Standard user — cred in AD description |
| diana.prince | Password2 | Standard user |
| barry.allen | Password3 | AS-REP roastable (DontReqPreAuth) |
| john.jones | Passsword4 | Standard user |
| hal.jordan | Password5 | Standard user |
| arthur.curry | Password6 | Standard user |

### Administrator Accounts

| Account | Password | Notes |
|---------|----------|-------|
| OSCP\Administrator | P@$$w0rd! | Domain Administrator |
| dark.knight | Password2025@# | Domain Admin — secondary DA |

### Service Accounts

| Account | Password | SPN |
|---------|----------|-----|
| SQLService | MYpassword123# | DC01/SQLService.OSCP.EXAM:60111 |

### SPN Configuration

```cmd
# Set SPN (run on DC01 as Administrator)
setspn.exe -a DC01/SQLService.OSCP.EXAM:60111 OSCP\SQLService

# List all SPNs in domain
setspn.exe -T OSCP.EXAM -Q */*
# Expected: DC01/SQLService.OSCP.EXAM:60111
```

---

## Requirements

| Component | Spec |
|-----------|------|
| RAM | 16GB recommended |
| Disk | 120GB free |
| Hypervisor | VirtualBox (free) |

### ISO Sources (Free / Legal)

```
# Windows Server 2025 Evaluation (180-day, fully functional)
https://www.microsoft.com/en-us/evalcenter/evaluate-windows-server-2025

# Windows 11 Enterprise Evaluation (90-day)
https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise

# Kali Linux (pre-built VirtualBox OVA — fastest)
https://www.kali.org/get-kali/#kali-virtual-machines
```

---

## Step 1 — VirtualBox Network Setup

```
File → Host Network Manager → Create
  IP: 192.168.56.1 / 255.255.255.0
  DHCP: Disabled

All VMs: Two network adapters
  Adapter 1: NAT          → internet (updates / tool downloads)
  Adapter 2: Host-Only    → 192.168.56.0/24 lab network
```

---

## Step 2 — DC01 Setup (Windows Server 2025)

```
VM: 4GB RAM, 2 CPU, 60GB disk
OS: Windows Server 2025 (Desktop Experience)

Static IP (inside VM):
  IP: 192.168.56.100
  Subnet: 255.255.255.0
  Gateway: 192.168.56.1
  DNS: 127.0.0.1  ← points to itself after DC promotion

Rename computer: DC01 → reboot
```

---

## Step 3 — Promote DC01 to Domain Controller

```powershell
# Run on DC01 as Administrator

Install-WindowsFeature AD-Domain-Services -IncludeManagementTools

Install-ADDSForest `
  -DomainName "OSCP.EXAM" `
  -DomainNetbiosName "OSCP" `
  -InstallDns:$true `
  -SafeModeAdministratorPassword (ConvertTo-SecureString "P@ssword123!" -AsPlainText -Force) `
  -Force:$true

# VM reboots automatically — login as OSCP\Administrator after
```

---

## Step 4 — Create Domain Users and Service Accounts

```powershell
# Run on DC01 as OSCP\Administrator

# Create OUs
New-ADOrganizationalUnit -Name "Corp Users"     -Path "DC=OSCP,DC=EXAM"
New-ADOrganizationalUnit -Name "Corp Computers" -Path "DC=OSCP,DC=EXAM"
New-ADOrganizationalUnit -Name "Service Accounts" -Path "DC=OSCP,DC=EXAM"

# Create domain users
$users = @(
    @{ Name="Clark Kent";   Sam="clark.kent";   Pass="Password1" },
    @{ Name="Diana Prince"; Sam="diana.prince"; Pass="Password2" },
    @{ Name="Barry Allen";  Sam="barry.allen";  Pass="Password3" },
    @{ Name="John Jones";   Sam="john.jones";   Pass="Passsword4" },
    @{ Name="Hal Jordan";   Sam="hal.jordan";   Pass="Password5" },
    @{ Name="Arthur Curry"; Sam="arthur.curry"; Pass="Password6" }
)

foreach ($u in $users) {
    New-ADUser `
      -Name $u.Name `
      -SamAccountName $u.Sam `
      -UserPrincipalName "$($u.Sam)@OSCP.EXAM" `
      -AccountPassword (ConvertTo-SecureString $u.Pass -AsPlainText -Force) `
      -Enabled $true `
      -Path "OU=Corp Users,DC=OSCP,DC=EXAM"
}

# Create second Domain Admin account
New-ADUser `
  -Name "Dark Knight" `
  -SamAccountName "dark.knight" `
  -UserPrincipalName "dark.knight@OSCP.EXAM" `
  -AccountPassword (ConvertTo-SecureString "Password2025@#" -AsPlainText -Force) `
  -Enabled $true `
  -Path "OU=Corp Users,DC=OSCP,DC=EXAM"

Add-ADGroupMember -Identity "Domain Admins" -Members "dark.knight"

# Create service account with SPN (Kerberoasting target)
New-ADUser `
  -Name "SQL Service" `
  -SamAccountName "SQLService" `
  -UserPrincipalName "SQLService@OSCP.EXAM" `
  -AccountPassword (ConvertTo-SecureString "MYpassword123#" -AsPlainText -Force) `
  -Enabled $true `
  -Path "OU=Service Accounts,DC=OSCP,DC=EXAM"

# Register SPN
setspn.exe -a DC01/SQLService.OSCP.EXAM:60111 OSCP\SQLService

# Verify
setspn.exe -T OSCP.EXAM -Q */*
```

---

## Step 5 — Configure Intentional Misconfigurations

```powershell
# Run on DC01 as Administrator

# 1. Weak password policy (easier lab cracking)
Set-ADDefaultDomainPasswordPolicy `
  -Identity "OSCP.EXAM" `
  -MinPasswordLength 4 `
  -ComplexityEnabled $false `
  -LockoutThreshold 0

# 2. Disable SMB signing (enables relay attacks)
Set-SmbServerConfiguration `
  -RequireSecuritySignature $false `
  -EnableSecuritySignature $false -Force

# 3. Add cred to user description (credential exposure misconfiguration)
Set-ADUser -Identity "clark.kent" `
  -Description "Temp password: Password1 — change after onboarding"

# 4. Set AS-REP roastable on barry.allen
Set-ADAccountControl -Identity "barry.allen" -DoesNotRequirePreAuth $true

# 5. Enable LLMNR (Responder capture target)
# Group Policy: Computer Config → Admin Templates → Network → DNS Client
# "Turn Off Multicast Name Resolution" → Disabled
```

---

## Step 6 — Join MS01 to Domain (Windows 11)

```
VM: 4GB RAM, 2 CPU, 50GB disk, Windows 11 Enterprise

Static IP:
  192.168.56.101 / 255.255.255.0
  DNS: 192.168.56.100

Local accounts:
  CLIENT01 / Password1!
  Administrator / Password1!

Join domain:
  Settings → System → About → Domain
  Domain: OSCP.EXAM
  Credentials: OSCP\Administrator / P@$$w0rd!
  Rename: MS01
  Reboot
```

### Configure AutoLogon on MS01 (Credential Exposure Target)

```cmd
# Run on MS01 as Administrator after domain join
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultUserName /d "clark.kent" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultPassword /d "Password1" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultDomainName /d "OSCP" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v AutoAdminLogon /d "1" /f

# Verify
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
```

---

## Step 7 — Join MS02 to Domain (Windows 11)

```
VM: 4GB RAM, 2 CPU, 50GB disk, Windows 11 Enterprise

Static IP:
  192.168.56.102 / 255.255.255.0
  DNS: 192.168.56.100

Local accounts:
  CLIENT02 / Password2!
  Administrator / Password2!

Join domain:
  Domain: OSCP.EXAM
  Credentials: OSCP\Administrator / P@$$w0rd!
  Rename: MS02
  Reboot
```

---

## Step 8 — Configure Kali

```bash
# Set static IP on Host-Only adapter
sudo nmtui
# Adapter: Host-Only
# IP: 192.168.56.10 / 255.255.255.0

# Add hosts
cat >> /etc/hosts << EOF
192.168.56.100 dc01.oscp.exam oscp.exam dc01 DC01
192.168.56.101 ms01.oscp.exam ms01 MS01
192.168.56.102 ms02.oscp.exam ms02 MS02
EOF

# Sync time with DC (avoid Kerberos clock skew)
sudo ntpdate 192.168.56.100

# Test
nxc smb 192.168.56.100
nxc smb 192.168.56.101
nxc smb 192.168.56.102
```

---

## Lab Attack Flow — Practice Checklist

```
PHASE 1 — RECON
[ ] nmap DC01 (192.168.56.100) → confirm ports 53, 88, 389, 445, 5985
[ ] nmap MS01, MS02 → workstation attack surface
[ ] nxc smb 192.168.56.0/24 → fingerprint all hosts

PHASE 2 — ENUMERATION (No Creds)
[ ] SMB null session: nxc smb 192.168.56.100 -u '' -p ''
[ ] RID brute: impacket-lookupsid ''@192.168.56.100
[ ] kerbrute userenum → validate users against OSCP.EXAM
[ ] ldapdomaindump → check clark.kent description for plaintext cred
[ ] Check password policy: lockout threshold, min length

PHASE 3 — CREDENTIAL ATTACKS
[ ] AS-REP roast barry.allen → hashcat -m 18200 → crack Password3
[ ] Kerberoast SQLService → hashcat -m 13100 → crack MYpassword123#
[ ] Password spray → try Password1 / Password2 against user list
[ ] Responder -A → capture LLMNR hashes

PHASE 4 — LATERAL MOVEMENT
[ ] evil-winrm → MS01 with clark.kent:Password1
[ ] reg query Winlogon → find AutoLogon creds on MS01
[ ] PTH between MS01 and MS02 with local admin hash (same pass)
[ ] nxc smb 192.168.56.0/24 -u Administrator -H HASH --local-auth

PHASE 5 — PRIVILEGE ESCALATION
[ ] BloodHound → collect → mark owned → find path to dark.knight or DA
[ ] certipy-ad find → check ADCS templates
[ ] ACL edges → WriteDACL / GenericAll / ForceChangePassword

PHASE 6 — DOMAIN DOMINANCE
[ ] DCSync as dark.knight: secretsdump OSCP.EXAM/dark.knight@192.168.56.100
[ ] Dump all NTLM hashes → save to loot/
[ ] krbtgt hash → forge Golden Ticket
[ ] Confirm DA access: nxc smb 192.168.56.100 -u administrator -H HASH
```

---

## VM Snapshots (Recommended)

```
Each VM — create snapshots at:
  "01-Clean"        → after domain join, before any attack
  "02-Post-access"  → after first foothold
  "03-Post-DA"      → after Domain Admin achieved

Revert to "01-Clean" to practice the same attack chain again from scratch.
```

---

## Troubleshooting

```bash
# Kerberos clock skew error
sudo ntpdate 192.168.56.100

# Domain not resolving
nslookup dc01.oscp.exam 192.168.56.100
# If fails: check /etc/hosts and Kali DNS setting

# SMB null session denied
nxc smb 192.168.56.100 -u '' -p ''
# If denied: try guest login: -u 'guest' -p ''

# BloodHound CE won't start
cd /home/kali/Arsenal/ActiveDirectory/BloodHoundCE
sudo docker-compose up -d
sudo docker logs bloodhoundce-bloodhound-1 | grep -i pass
```

---

[← Back to Main](../README.md)
