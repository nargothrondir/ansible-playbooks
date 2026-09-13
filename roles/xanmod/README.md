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
| `xanmod_variant` | `x64v3` | CPU/PSABI level: `x64v1`…`x64v4`, or `auto` to read it from this host's CPU flags |
| `xanmod_variant_max` | `x64v3` | Ceiling applied when `xanmod_variant` is `auto` |
| `xanmod_package` | `linux-xanmod-{{ xanmod_variant }}` | Package to install |
| `xanmod_apt_arch` | `amd64` | APT repository architecture |
| `xanmod_reboot` | `false` | Reboot into the new kernel when it was just installed (handler) |

### Choosing the variant

XanMod ships one kernel per x86-64 microarchitecture level. A kernel built for a
level the CPU does not implement **does not boot**, and on a VPS that appears as
a node which never comes back from its reboot — with no console and nothing in
any log tying it to the run that caused it.

So the role establishes the level before installing anything, by reading
`/proc/cpuinfo` and applying the flag tables from XanMod's own
`check_x86-64_psabi.sh`. The script is not downloaded or executed: reproducing
eight lines of awk avoids running a fetched script as root, and avoids depending
on `dl.xanmod.org` being reachable from a node that may sit behind censorship.

Two things follow from the detected level.

**The assert always runs.** A configured variant above what the CPU implements
stops the play before `apt` is called. A host already running `x64v3` implements
at least level 3, so this is silent on healthy nodes.

**`auto` is opt-in.** Set `xanmod_variant: auto` and the role installs
`min(detected level, xanmod_variant_max)`. It is not the default because
changing the variant on a running node swaps its kernel, which no routine run
should do uninvited; `provision-node.yml` enables it for fresh nodes, as it
already does for `xanmod_reboot`.

**The ceiling is deliberate.** `xanmod_variant_max` defaults to `x64v3` rather
than to whatever the CPU reports, because a VPS is not its hardware: providers
migrate guests between hosts, and an `x64v4` kernel stops booting the moment the
guest lands on a machine without AVX-512. That failure arrives detached from any
change you made. `x64v3` is AVX2 — satisfied by anything sold in a decade, and
XanMod's own recommended build.

Note that the role does **not** check whether a XanMod kernel is already
running. `apt` with `state: present` reports `ok` for an installed package and
changes nothing, so there is nothing to guard; and the running kernel is the
wrong signal anyway, since a node that has installed XanMod but not yet rebooted
is still running the stock one.

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
