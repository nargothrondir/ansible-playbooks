# Роль: bootstrap

[🇬🇧 English](README.md) · 🇷🇺 Русский

## Описание

Первичная подготовка только что созданного сервера. Подключается под `root`
(по SSH-ключу) и создаёт пользователя-автоматизатора Ansible **только по
ключу** (его пароль заблокирован) с беспарольным sudo.

Роль **не** усиливает SSH (не отключает вход root): этот шаг намеренно отложен,
пока вы сами не решите его закрыть.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `bootstrap_hostname` | `""` | Hostname системы (пусто = не менять); становится именем пира NetBird / mesh-DNS-именем |
| `bootstrap_user` | `ansible` | Имя создаваемого пользователя |
| `bootstrap_user_shell` | `/bin/bash` | Командная оболочка |
| `bootstrap_user_groups` | `[sudo]` | Дополнительные группы |
| `bootstrap_authorized_keys` | `[]` | **Обязательно** — публичный(е) SSH-ключ(и) |
| `bootstrap_passwordless_sudo` | `true` | Разворачивать sudoers с NOPASSWD:ALL |

`bootstrap_authorized_keys` должна содержать хотя бы один публичный ключ — роль
это проверяет. У пользователя нет пароля (только ключ), поэтому повторные
запуски идемпотентны.

## Зависимости

Коллекция `ansible.posix` (для `authorized_key`). Закреплена в `requirements.yml`.

## Пример

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

## Поддерживаемые ОС

Debian (bookworm, trixie), Ubuntu (jammy, noble).
