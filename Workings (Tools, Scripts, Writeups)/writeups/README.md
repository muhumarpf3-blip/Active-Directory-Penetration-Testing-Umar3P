# 📝 Writeups

Step-by-step machine writeups — full attack chain documented per machine.

---

## HackTheBox

| Machine | Difficulty | Key Techniques | Writeup |
|---------|------------|----------------|---------|
| Forest | Easy | AS-REP Roast → WriteDACL → DCSync | [HTB-FOREST.md](HTB-FOREST.md) |
| Active | Easy | GPP cpassword → Kerberoasting → PSExec | [HTB-ACTIVE.md](HTB-ACTIVE.md) |
| Sauna | Easy | AS-REP Roast → AutoLogon creds → DCSync | [HTB-SAUNA.md](HTB-SAUNA.md) |

## TryHackMe

| Machine | Key Techniques | Writeup |
|---------|----------------|---------|
| Attacktive Directory | Kerbrute → AS-REP Roast → SMB → secretsdump → PTH | [THM-ATTACKTIVE-DIRECTORY.md](THM-ATTACKTIVE-DIRECTORY.md) |
| Enterprise | SMB enum → Kerberoasting → GPO abuse → SYSTEM | [THM-ENTERPRISE.md](THM-ENTERPRISE.md) |

---

## Writeup Format

Each writeup follows the same structure:

```
1. Machine Info (IP, domain, hostname, key techniques)
2. Environment Setup (export vars, /etc/hosts, mkdir)
3. Recon (nmap output, open ports)
4. Domain Enumeration (users discovered)
5. Credential Attacks (hashes, cracks)
6. Lateral Movement (initial shell)
7. Privilege Escalation (BloodHound / ACL / ADCS path)
8. Domain Dominance (DCSync / proof)
9. Attack Chain Summary (visual flow)
10. Key Takeaways
```

---

[← Back to Main](../README.md)
