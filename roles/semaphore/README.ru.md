# Роль: semaphore

[🇬🇧 English](README.md) · 🇷🇺 Русский

## Описание

Разворачивает [Semaphore](https://semaphoreui.com/) (веб-интерфейс для Ansible)
на управляющем узле через Docker Compose со встроенной БД SQLite. Публикует UI
на локальном порту для уже имеющегося reverse-proxy; опционально подключается к
внешней Docker-сети.

Требуется Docker с плагином Compose v2 на целевом хосте.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `semaphore_image` | `semaphoreui/semaphore:v2.19.8` | Закреплённый образ |
| `semaphore_data_dir` | `/opt/semaphore` | Каталог compose-файла (данные — в именованных томах) |
| `semaphore_bind` | `127.0.0.1:3000` | Хост-привязка публикуемого порта |
| `semaphore_internal_port` | `3000` | Порт контейнера |
| `semaphore_external_network` | `""` | Внешняя Docker-сеть для подключения (опц.) |
| `semaphore_admin_user` | `admin` | Логин администратора |
| `semaphore_admin_name` | `Admin` | Отображаемое имя |
| `semaphore_admin_email` | `admin@localhost` | Email администратора |
| `semaphore_db_dialect` | `sqlite` | Бэкенд БД (встроенный; bolt устарел) |
| `semaphore_admin_password` | _(обязательно, vault)_ | Пароль администратора |
| `semaphore_access_key_encryption` | _(обязательно, vault)_ | base64-ключ 32 байта |

Сгенерировать ключ шифрования один раз: `head -c 32 /dev/urandom | base64`.

## Зависимости

Коллекция `community.docker` (закреплена в `requirements.yml`); Docker + Compose v2
на хосте.

## Пример

```yaml
- name: Deploy Semaphore on the control node
  hosts: control
  become: true
  roles:
    - role: semaphore
```

Затем направь свой reverse-proxy на `semaphore_bind` (или подключи общую
Docker-сеть через `semaphore_external_network`).

## Поддерживаемые ОС

Debian (bookworm, trixie), Ubuntu (jammy, noble).
