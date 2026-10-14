# 🔍 01 — Recon & Initial Foothold

---

## Attack Order

```
1. Host discovery → identify DC
2. Full TCP port scan → map attack surface
3. Service scan on open ports → version, OS, SMB signing
4. DC-specific port check (53, 88, 389, 445, 5985)
5. DNS enumeration → zone transfer, subdomains
6. LDAP / RPC anonymous probe → confirm domain name
```

---

## Environment Setup

```bash
export ip=10.10.10.x
export domain=corp.local
export user=
export pass=
echo "$ip $domain" >> /etc/hosts
mkdir -p scan enum creds loot
```

---

## Port Scanning

```bash
# Quick scan — top 1000 ports
nmap -sC -sV -oN scan/nmap-quick.txt $ip

# Full TCP — all 65535 ports
nmap -p- -T4 --min-rate=1000 -oN scan/nmap-full.txt $ip

# Service + script scan on discovered ports
nmap -p 53,88,135,139,389,445,464,593,636,3268,3269,3389,5985,9389 \
  -sV -sC -oN scan/nmap-svc.txt $ip

# General vuln scan
nmap -p- --script vuln -oN scan/nmap-vuln.txt $ip

# UDP top 100 — catches SNMP (161), DNS (53)
sudo nmap -sU --top-ports 100 -oN scan/nmap-udp.txt $ip

# Rustscan → fast open ports → pipe to nmap
rustscan -a $ip --ulimit 5000 -- -sV -sC -oN scan/rustscan.txt
```

---

## DC Identification

```bash
# DC = Kerberos (88) + LDAP (389) + SMB (445) + DNS (53) open together
nmap -p 53,88,389,445 $ip --open

# Fingerprint with netcat
nc -nv $ip 88
nc -nv $ip 389
```

### DC Port Reference

| Port | Service | Attack Vector |
|------|---------|---------------|
| 53 | DNS | Zone transfer, subdomain enum |
| 88 | Kerberos | AS-REP roast, spray, ticket attacks |
| 135 | RPC | `rpcclient` enumdomusers |
| 139/445 | SMB | Null session, RID brute, shares |
| 389/636 | LDAP/S | ldapdomaindump, anonymous dump |
| 3268/3269 | Global Catalog | Forest-wide LDAP |
| 3389 | RDP | PTH with restricted admin |
| 5985/5986 | WinRM | evil-winrm |

---

## SMB Fingerprinting

```bash
# Check SMB version and signing status
nmap -p 445 --script smb2-security-mode $ip
nxc smb $ip

# SMB signing disabled = relay attacks possible
# Look for: "Message signing enabled but not required"
```

---

## DNS Enumeration

```bash
# Zone transfer
dig axfr $domain @$ip

# All record types
dig any $domain @$ip

# Reverse lookup
dig -x $ip @$ip

# Subdomain brute
gobuster dns -d $domain \
  -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt \
  -r $ip
```

---

## LDAP Anonymous Probe

```bash
# Confirm base DN / domain name
ldapsearch -x -H ldap://$ip -s base namingContexts

# Full anonymous dump (if allowed)
ldapsearch -x -b "DC=corp,DC=local" -H ldap://$ip
```

---

## RPC Anonymous Probe

```bash
rpcclient -U "" -N $ip
# Inside:
rpcclient> srvinfo
rpcclient> enumdomains
rpcclient> querydominfo
# If enumdomusers works here → no creds needed for full user list
```

---

## Key Findings to Record

```bash
echo "DC IP: $ip"          > enum/findings.txt
echo "Domain: $domain"    >> enum/findings.txt
echo "Open ports: [list]" >> enum/findings.txt
echo "SMB signing: "      >> enum/findings.txt
echo "LDAP anon: yes/no"  >> enum/findings.txt
```

---

**MITRE ATT&CK:** T1595 (Active Scanning) · T1590 (Gather Victim Network Info) · T1018 (Remote System Discovery)

[← Back to Main](../README.md) | [Next: Domain Enumeration →](../02-domain-enum/README.md)
