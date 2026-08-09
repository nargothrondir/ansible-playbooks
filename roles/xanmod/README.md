# Role: xanmod

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Installs the [XanMod](https://xanmod.org/) performance kernel from the official
XanMod APT repository (signing key → `/etc/apt/keyrings/xanmod.asc`, deb822
source → `/etc/apt/sources.list.d/xanmod.sources`). Idempotent.

**A reboot is required** to boot into the new kernel; the role does not reboot.
The `upgrade` role reboots once it detects the running kernel is no longer the
newest installed one (or reboot by hand).

Note: `deb.xanmod.org` is a third-party mirror and may be intermittently blocked
in some regions (see issue #3 for the `ru` node).

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `xanmod_variant` | `x64v3` | CPU/PSABI level: `x64v1`/`x64v2`/`x64v3`. Detect with XanMod's `check_x86-64_psabi.sh` |
| `xanmod_package` | `linux-xanmod-{{ xanmod_variant }}` | Package to install |
| `xanmod_apt_arch` | `amd64` | APT repository architecture |
| `xanmod_reboot` | `false` | Reboot into the new kernel when it was just installed (handler) |

## Dependencies

None.

## Example

```yaml
- hosts: managed
  become: true
  roles:
    - role: xanmod
```

## Supported OS

Debian 12/13, Ubuntu 24.04 (`os_family == 'Debian'`), x86-64.
