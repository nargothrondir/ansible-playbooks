# Роль: hawser

[🇬🇧 English](README.md) · 🇷🇺 Русский

## Описание

Разворачивает агент [Hawser](https://github.com/Finsys/hawser) (для
[Dockhand](https://github.com/Finsys/dockhand)) на удалённом Docker-хосте в
**edge-режиме** — агент сам подключается к Dockhand по WebSocket наружу, поэтому
входящий порт/проброс не нужен (удобно для VPS/NAT и хостов за блокировками).

Каждый хост — отдельное окружение Dockhand со **своим токеном**.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `hawser_image` | `ghcr.io/finsys/hawser:0.2.46` | Закреплённый образ агента |
| `hawser_dir` | `/opt/hawser` | Каталог compose-файла агента |
| `hawser_stacks_dir` | `/opt/hawser-stacks` | `STACKS_DIR` для стеков, управляемых Hawser |
| `hawser_request_timeout` | `180` | `REQUEST_TIMEOUT` агента (сек); дефолт 30 с обрывает долгие холодные деплои |
| `hawser_dockhand_url` | _(обязательна)_ | Edge-endpoint Dockhand (`wss://…/api/hawser/connect`), в `group_vars/all` |
| `hawser_token` | _(обязательна, vault)_ | Токен агента на хост (напр. из словаря `hawser_host_tokens` в `group_vars/managed/vault.yml`) |

## Зависимости

`community.docker` (для `docker_compose_v2`). На хосте должен быть установлен Docker.

## Пример

```yaml
- name: Deploy Hawser
  hosts: managed
  become: true
  tasks:
    - ansible.builtin.include_role:
        name: hawser
      when: hawser_token | default('') | length > 0
```

## Поддерживаемые ОС

Debian (bookworm, trixie), Ubuntu (jammy, noble).
