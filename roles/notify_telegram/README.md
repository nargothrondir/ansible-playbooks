# Role: notify_telegram

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Sends a single message to a Telegram chat via the Bot API (`uri`, no extra
collections). Intended to run on the controller (`delegate_to: localhost`) so
managed hosts don't need outbound access to Telegram.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `notify_telegram_bot_token` | `{{ telegram_bot_token }}` | Bot API token — callers pass it from OpenBao `infra/telegram` |
| `notify_telegram_chat_id` | `{{ telegram_chat_id }}` | Target chat id |
| `notify_telegram_message_thread_id` | `""` | Forum topic id (`message_thread_id`); empty = General topic |
| `notify_telegram_silent` | `false` | Send without sound (`disable_notification`); message still appears |
| `notify_telegram_parse_mode` | `""` | `""` (plain), `HTML` or `MarkdownV2`; the caller must escape dynamic content |
| `notify_telegram_message` | `""` | Message text (required) |

The token is handled with `no_log: true`. The token and chat id default to the
global `telegram_*` vars (see `group_vars/all/`).

## Dependencies

None (uses `ansible.builtin.uri`).

## Example

```yaml
- name: Notify
  ansible.builtin.include_role:
    name: notify_telegram
  vars:
    notify_telegram_message: "Deploy finished"
  run_once: true
  delegate_to: localhost
```

## Supported OS

Runs on the controller; any platform with Python and network access to
api.telegram.org.
