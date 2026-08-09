# Роль: netbird

[🇬🇧 English](README.md) · 🇷🇺 Русский

## Описание

Устанавливает агент [NetBird](https://netbird.io/) из официального
APT-репозитория (ключ подписи → `/etc/apt/keyrings/netbird.asc`,
deb822-источник → `/etc/apt/sources.list.d/netbird.sources`), включает сервис и
присоединяет хост к мешу без интерактива — по **setup-ключу**.

Присоединение идемпотентно (fetch-then-guard): сначала читается `netbird
status`, и `netbird up` выполняется только если хост ещё не подключён — поэтому
роль безопасно гонять по хостам, уже вступившим в меш (например, текущий флот).

Переменная `netbird_management_url` направляет агент на self-hosted
management-сервер (issue #6); пустая — используется облако NetBird.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `netbird_setup_key` | `""` | Переиспользуемый setup-ключ (секрет) — через vault |
| `netbird_management_url` | `""` | URL self-hosted management; пусто = облако NetBird |
| `netbird_ssh_server` | `true` | Передать `--allow-server-ssh` при join — запасной вход для флота (root-логин сознательно не предусмотрен, `--disable-ssh-auth` не передаётся никогда). Требует открытого порта 22022 на mesh-интерфейсе, см. `roles/ufw`. Применяется только при фактическом join |
| `netbird_apt_arch` | `amd64` | Архитектура APT-репозитория |

Setup-ключ обрабатывается с `no_log: true`.

## Зависимости

Нет.

## Пример

```yaml
- hosts: managed
  become: true
  roles:
    - role: netbird
```

## Поддерживаемые ОС

Debian 12/13, Ubuntu 22.04/24.04 (`os_family == 'Debian'`).
