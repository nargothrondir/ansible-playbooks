# Role: apt_sources

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Writes the Debian archive sources in one canonical deb822 file and removes
whatever arrangement the provider image shipped. Third-party repositories are
left alone — `roles/docker`, `roles/netbird`, `roles/xanmod` and
`roles/crowdsec` each own theirs.

## Why

The fleet was assembled from five provider images, and every one of them
arranged apt differently. Measured across all five nodes on 2026-08-14:

| | layout | scheme | components | security host | backports |
|---|---|---|---|---|---|
| A | `sources.list` | http | `main non-free-firmware` | `security.debian.org/debian-security` | no |
| B | `sources.list` | http | `main non-free-firmware` | `deb.debian.org/debian-security` | no |
| C | `sources.list` | https | `main contrib non-free non-free-firmware` | `security.debian.org/debian-security` | no |
| D | fragments in `sources.list.d/` | http | `main` | `security.debian.org/` | **yes** |
| E | `debian.sources` (deb822) | https | — | `deb.debian.org/debian-security` | no |

Not one of them pointed at a provider mirror, which was the original worry. The
real problem was narrower and more annoying: **the same `apt install` could
succeed on one node and fail on another**, because one host had `contrib` and
`non-free` while another had `main` alone.

## What it does

- writes `/etc/apt/sources.list.d/debian.sources` — https, `main
  non-free-firmware`, security from `security.debian.org/debian-security`
- removes `/etc/apt/sources.list` and any file in `sources.list.d/` that points
  at a Debian archive
- backs up everything it removes first, with a suffix apt does not read
- refreshes the package lists and **asks apt** what it now fetches

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `apt_sources_uri` | `https://deb.debian.org/debian` | Main archive |
| `apt_sources_security_uri` | `https://security.debian.org/debian-security` | Security archive — its own host, and the canonical path |
| `apt_sources_components` | `main non-free-firmware` | `contrib`/`non-free` deliberately absent; nothing on the fleet came from them |
| `apt_sources_backports` | `false` | Adds `<suite>-backports` when true |
| `apt_sources_suite` | `{{ ansible_facts['distribution_release'] }}` | Taken from the host — a hardcoded codename breaks on the next release |
| `apt_sources_file` | `/etc/apt/sources.list.d/debian.sources` | Where the canonical file goes |
| `apt_sources_keyring` | `/usr/share/keyrings/debian-archive-keyring.gpg` | `Signed-By` for both stanzas |
| `apt_sources_backup_suffix` | `.pre-apt-sources.bak` | apt reads only `*.list` and `*.sources`, so backups can sit beside the originals |
| `apt_sources_require_debian` | `true` | Refuses to run on Ubuntu, whose archive and component names differ |

## Two decisions worth knowing

**https, not http.** Signatures protect integrity either way — that is Debian's
own position and why http is still the default. https additionally hides *which
packages* a host fetches from anyone watching the wire, and one node on this
fleet sits behind censorship.

**deb822, not one-line.** The reason is `Signed-By`. In deb822 it is a field; in
the one-line format it is a bracket option that is easy to omit — and an omitted
`Signed-By` means apt validates that repository against **every** key in the
trusted keyring, which is how a third-party repository quietly becomes as trusted
as Debian itself.

## Matching by content, not by name

The files to remove are found by looking for a Debian archive URI inside them,
because their names differ per provider image: `sources.list`, `default.list`,
`updates.list`, `security.list`, `debian.sources`. The third-party repositories
point at `download.docker.com`, `pkgs.netbird.io`, `deb.xanmod.org` and
`packagecloud.io`, so they cannot match and are never touched.

Files under two bytes are also removed: they cannot hold `deb URI suite
component`, so they declare nothing. One provider image left a one-byte file
literally named `.list`.

## Verified against apt, not against the files

After writing, the role asks `apt-get indextargets` what apt will actually fetch
and fails if a Debian archive appears that the role did not declare. Writing a
correct file is not the same as being the only file — several nodes had a
plausible-looking `sources.list` beside a `sources.list.d/` that was also being
read, and apt takes the union.

## Dependencies

None. Debian only — the assert refuses to run elsewhere.

## Example

```yaml
- name: Normalise apt sources
  hosts: lab
  become: true
  roles:
    - apt_sources
```

## Supported OS

Debian 12 (bookworm), Debian 13 (trixie). **Not Ubuntu** — the control host is
deliberately out of scope, and the assert enforces it.
