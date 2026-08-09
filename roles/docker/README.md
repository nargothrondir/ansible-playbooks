# Role: docker

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Installs Docker Engine and the Compose plugin from the **official Docker APT
repository** (deb822 source `/etc/apt/sources.list.d/docker.sources`, signing
key fetched and pinned by the module), enables the service and adds the given
users to the `docker` group so they can use the CLI without sudo.

Note: adding a user to the `docker` group grants root-equivalent access on the
host — only automation/admin users belong there.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `docker_packages` | docker-ce, docker-ce-cli, containerd.io, docker-buildx-plugin, docker-compose-plugin | Packages to install |
| `docker_apt_arch` | `amd64` | APT repository architecture |
| `docker_users` | `[{{ bootstrap_user }}]` | Users added to the `docker` group |

## Dependencies

None (installs its own prerequisites: ca-certificates, python3-debian).

## Example

```yaml
- hosts: lab
  become: true
  roles:
    - role: common
    - role: docker
```

## Supported OS

Debian 12/13, Ubuntu 22.04/24.04 (`os_family == 'Debian'`), x86_64.
