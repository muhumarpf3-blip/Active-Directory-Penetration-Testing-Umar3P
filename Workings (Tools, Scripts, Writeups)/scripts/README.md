# 🛠️ Scripts

Custom Python tools for AD penetration testing workflows.  
Built around impacket and netexec — designed for real lab and engagement use.

---

## Tools

| Script | Purpose | Creds Required |
|--------|---------|----------------|
| [bloodhound-collector.py](bloodhound-collector.py) | BloodHound CE collection wrapper with import instructions | Yes |
| [password-spray.py](password-spray.py) | Safe spray with lockout warning and confirm prompt | No |

---

## Dependencies

```bash
# netexec (recommended — covers most use cases)
sudo apt install netexec -y

# bloodhound-python (alternative collector)
pip install bloodhound --break-system-packages

# impacket (required for spray script)
pip install impacket --break-system-packages
```

---

## Usage

### bloodhound-collector.py

```bash
# Full collection (All — includes sessions, ACLs, GPOs)
python3 bloodhound-collector.py -d corp.local --dc 10.10.10.100 -u jsmith -p Password123!

# DCOnly (fast — no workstation sessions, less noise)
python3 bloodhound-collector.py -d corp.local --dc 10.10.10.100 -u jsmith -p Password123! -c DCOnly

# Use bloodhound-python instead of nxc
python3 bloodhound-collector.py -d corp.local --dc 10.10.10.100 -u jsmith -p Password123! --tool bloodhound-python
```

### password-spray.py

```bash
# Single password spray via kerbrute (default)
python3 password-spray.py -u enum/users.txt -p Password123! -d corp.local --dc 10.10.10.100

# Via netexec SMB
python3 password-spray.py -u enum/users.txt -p Password123! -d corp.local --dc 10.10.10.100 --method nxc

# With delay (quieter — 5s between users)
python3 password-spray.py -u enum/users.txt -p Password123! -d corp.local --dc 10.10.10.100 --delay 5

# Specify lockout threshold (for warning display)
python3 password-spray.py -u enum/users.txt -p Password123! -d corp.local --dc 10.10.10.100 --lockout-threshold 5

# ⚠️ Always retrieve password policy before spraying
# nxc smb $ip -u $user -p $pass --pass-pol
```

---

> ⚠️ **For authorized penetration testing only.**  
> Always retrieve the domain password policy before spraying — know the lockout threshold.

[← Back to Main](../README.md)
