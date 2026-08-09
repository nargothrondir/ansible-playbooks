# Роль: beszel_agent

[🇬🇧 English](README.md) · 🇷🇺 Русский

## Описание

Устанавливает агент мониторинга [Beszel](https://beszel.dev) как **бинарник +
systemd-сервис** (не Docker), перенимая раскладку официального установщика
Beszel (юзер `beszel`, бинарь в `/opt/beszel-agent`, sandbox-unit).

- **WebSocket-подключение:** агент сам звонит на хаб (`HUB_URL` + per-node
  `TOKEN`), поэтому **не открывает ни одного входящего порта** — по духу
  private-by-default.
- **Авторегистрация через API хаба:** роль сама регистрирует ноду в хабе
  (PocketBase) и выдаёт ей **per-node токен** через API — а также **сама тянет
  публичный ключ хаба** и владельца. Руками задаётся только суперюзер-креды (в
  vault). Идемпотентно (токен существующей системы дочитывается). Отключается
  `beszel_agent_register: false` (тогда токен/ключ задаёшь сам).
- **Учитывает самообновление:** бинарь ставится только если отсутствует
  (`creates`-guard). Дальше Beszel обновляет себя сам, роль версию не
  перепиновывает и не дерётся — пиннутая версия лишь для первой установки на
  голую ноду.
- **Статистика контейнеров:** юзер агента добавляется в группу `docker` для
  чтения `/var/run/docker.sock`.
- Токен рендерится в unit, который пишется `0600` (только root) с `no_log`, так
  что не world-readable и не в логах.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `beszel_agent_version` | `0.18.7` | Версия бинарника для первой установки (потом Beszel сам обновляет). |
| `beszel_agent_arch` | `amd64` | Архитектура релиза. |
| `beszel_agent_hub_url` | `""` | **Обязательна** — URL хаба (WebSocket + API регистрации). Задаётся в инвентаре; в роли не дефолтится, чтобы реальное имя хоста не уехало в репозиторий. |
| `beszel_agent_key` | `""` | Публичный ключ хаба. Авто-фетч при регистрации; задаётся руками только если `register` выключён. |
| `beszel_agent_token` | `""` | Per-node токен. Пустой — заполняется авторегистрацией (или задаёшь сам, если выключена). |
| `beszel_agent_register` | `true` | Регистрировать ноду через API; тянет ключ/владельца и выдаёт токен. |
| `beszel_agent_admin_email` | `vault_beszel_admin_email` | Email **суперюзера** PocketBase хаба (регистрация). |
| `beszel_agent_admin_password` | `vault_beszel_admin_password` | Пароль суперюзера — **ansible-vault**. |
| `beszel_agent_owner_email` | `""` | Dashboard-владелец систем; пусто = единственный/первый юзер. |
| `beszel_agent_system_name` | `{{ inventory_hostname }}` | Имя системы в хабе. |
| `beszel_agent_system_host` | `{{ inventory_hostname }}` | Отображаемый host (для WebSocket номинально). |
| `beszel_agent_docker_group` | `true` | Добавить юзера агента в `docker` для статистики контейнеров. |
| `beszel_agent_extra_filesystems` | `""` | `EXTRA_FILESYSTEMS` (доп. диски для мониторинга). |
| `beszel_agent_port` | `45876` | `PORT` (слушатель SSH-режима; не используется при заданном `HUB_URL`). |

## Зависимости

Нет (на уровне роли). Docker должен присутствовать, если
`beszel_agent_docker_group: true`. Авторегистрации нужны **только**
суперюзер-креды хаба (в vault); ключ хаба и владельца она тянет из PocketBase API.

## Пример

```yaml
# group_vars/*/vault.yml   (единственное, что задаётся руками)
vault_beszel_admin_email: "admin@example.com"
vault_beszel_admin_password: "…"
```

```yaml
- hosts: fleet:!panel
  become: true
  roles:
    - beszel_agent
```

## Поддерживаемые ОС

Debian 12/13, Ubuntu 22.04/24.04 (`os_family == 'Debian'`).
