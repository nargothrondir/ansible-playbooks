# Role: bootstrap

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

First-contact provisioning for a freshly created server. Connects as `root`
(SSH key) and creates the Ansible automation user as **key-only** (its password
is locked) with passwordless sudo.

The role does **not** harden SSH (e.g. disable root login). That step is
intentionally deferred until you decide to lock it down.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `bootstrap_hostname` | `""` | System hostname to set (empty = leave unchanged); becomes the NetBird peer / mesh DNS name |
| `bootstrap_user` | `ansible` | Name of the automation user to create |
| `bootstrap_user_shell` | `/bin/bash` | Login shell |
| `bootstrap_user_groups` | `[sudo]` | Supplementary groups |
| `bootstrap_authorized_keys` | `[]` | **Required** — SSH public key(s) to authorize |
| `bootstrap_passwordless_sudo` | `true` | Deploy a NOPASSWD:ALL sudoers drop-in |

`bootstrap_authorized_keys` must contain at least one public key — the role
asserts this. The user has no password (key-only), so re-runs are idempotent.

## Dependencies

Collection `ansible.posix` (for `authorized_key`). Pinned in `requirements.yml`.

## Example

```yaml
- name: Bootstrap automation user
  hosts: new_vps
  gather_facts: true
  vars:
    ansible_user: root
    ansible_ssh_private_key_file: "~/.ssh/admin_ed25519"
  roles:
    - role: bootstrap
```

## Supported OS

Debian (bookworm, trixie), Ubuntu (jammy, noble).
