# Роль: docker

[🇬🇧 English](README.md) · 🇷🇺 Русский

## Описание

Устанавливает Docker Engine и Compose-плагин из **официального APT-репозитория
Docker** (deb822-источник `/etc/apt/sources.list.d/docker.sources`, ключ
подписи модуль скачивает и пинует сам), включает сервис и добавляет указанных
пользователей в группу `docker` для работы с CLI без sudo.

Важно: членство в группе `docker` эквивалентно root-доступу на хосте — туда
допускаются только пользователи автоматизации/администраторы.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `docker_packages` | docker-ce, docker-ce-cli, containerd.io, docker-buildx-plugin, docker-compose-plugin | Устанавливаемые пакеты |
| `docker_apt_arch` | `amd64` | Архитектура APT-репозитория |
| `docker_users` | `[{{ bootstrap_user }}]` | Пользователи, добавляемые в группу `docker` |

## Зависимости

Нет (свои пререквизиты ставит сама: ca-certificates, python3-debian).

## Пример

```yaml
- hosts: lab
  become: true
  roles:
    - role: common
    - role: docker
```

## Поддерживаемые ОС

Debian 12/13, Ubuntu 22.04/24.04 (`os_family == 'Debian'`), x86_64.
