# Роль: dockhand

[🇬🇧 English](README.md) · 🇷🇺 Русский

## Описание

Разворачивает [Dockhand](https://github.com/Finsys/dockhand) (веб-UI для Docker)
на управляющем узле через Docker Compose. Управляет **локальным** Docker через
примонтированный сокет; удалённые хосты — через агент Hawser (см. роль
`hawser`). Данные — в именованном томе Docker. UI слушает loopback и рассчитан на
работу за reverse-proxy (Netbird-only / IP-allowlist).

> При первом запуске авторизация **отключена** — сразу включи её в
> **Settings → Authentication** и создай админ-пользователя.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `dockhand_image` | `fnsys/dockhand:v1.0.40` | Закреплённый образ |
| `dockhand_bind` | `127.0.0.1:3040` | Привязка UI на хосте (за прокси) |
| `dockhand_data_dir` | `/opt/dockhand` | Каталог compose-файла (данные — в томе) |
| `dockhand_puid` / `dockhand_pgid` | `1000` | UID/GID пользователя в контейнере |
| `dockhand_encryption_key` | _(обязательна, vault)_ | Base64 AES-256 ключ (44 символа) для шифрования кредов |

`dockhand_encryption_key` — base64 от 32 байт (`openssl rand -base64 32`),
задаётся через ansible-vault.

## Зависимости

`community.docker` (для `docker_compose_v2`). На хосте должен быть установлен Docker.

## Пример

```yaml
- name: Deploy Dockhand
  hosts: control
  become: true
  roles:
    - role: dockhand
```

## Поддерживаемые ОС

Debian (bookworm, trixie), Ubuntu (jammy, noble).
