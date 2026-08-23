# Роль: notify_telegram

[🇬🇧 English](README.md) · 🇷🇺 Русский

## Описание

Отправляет одно сообщение в Telegram-чат через Bot API (`uri`, без сторонних
коллекций). Рассчитана на запуск с контроллера (`delegate_to: localhost`),
чтобы управляемым хостам не требовался доступ к Telegram.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `notify_telegram_bot_token` | `{{ telegram_bot_token }}` | Токен бота — вызывающий передаёт его из OpenBao `infra/telegram` |
| `notify_telegram_chat_id` | `{{ telegram_chat_id }}` | ID чата-получателя |
| `notify_telegram_message_thread_id` | `""` | ID топика (`message_thread_id`); пусто = General |
| `notify_telegram_silent` | `false` | Отправить без звука (`disable_notification`); сообщение всё равно приходит |
| `notify_telegram_parse_mode` | `""` | `""` (обычный), `HTML` или `MarkdownV2`; вызывающий сам экранирует динамику |
| `notify_telegram_message` | `""` | Текст сообщения (обязателен) |

Токен обрабатывается с `no_log: true`. Токен и chat id по умолчанию берутся из
глобальных переменных `telegram_*` (см. `group_vars/all/`).

## Зависимости

Нет (используется `ansible.builtin.uri`).

## Пример

```yaml
- name: Notify
  ansible.builtin.include_role:
    name: notify_telegram
  vars:
    notify_telegram_message: "Деплой завершён"
  run_once: true
  delegate_to: localhost
```

## Поддерживаемые ОС

Выполняется на контроллере; любая система с Python и доступом к
api.telegram.org.
