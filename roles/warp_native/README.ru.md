# Роль: warp_native

[English](README.md) · Русский

## Описание

Отдельный IPv4-интерфейс WireGuard `warp` для выбранного исходящего трафика
Xray. Через него идут только outbound с привязкой к `warp` и меткой **51888**.
Основная таблица маршрутов, NetBird `wt0`, UFW, CrowdSec и resolver сохраняются.

Роль владеет таблицей nftables `inet warp_native`: в output с приоритетом -10
отбрасываются `meta mark 51888 oifname != "warp"`. Остановка интерфейса не
удаляет правило. Дополнительно роль управляет IPv4 policy rule с приоритетом
10088 и таблицей 51888: default через `warp` с metric 10 и постоянный unreachable default с
metric 42760. Поэтому при перезагрузке nftables помеченный трафик также не
откатывается на обычный IP. `Table = off` запрещает wg-quick менять основную
таблицу; `DNS =` отсутствует.

Дополнительный firewall-сервис не включается. Drop-in для существующего
`nftables.service` добавляет восстановление собственных правил после
start/reload/stop, сохраняя команды поставщика. UFW меняет свои iptables-цепочки,
CrowdSec bouncer — отдельные таблицы. Произвольное ручное удаление policy rules
в эту гарантию не входит. Не удаляйте guard, пока профиль использует `warp-out`.

Предварительная проверка отклоняет чужую установку WARP, занятые метку,
приоритет и таблицы, конфликты масок, а также динамическую запись меток, для
которой нельзя исключить 51888. Проверяются nftables, iptables-legacy, policy
rules IPv4/IPv6 и метки WireGuard. Причину отказа нужно разобрать, а существующую
shell-установку мигрировать явно; автоматического захвата её файлов нет.

wgcf **2.3.1** закреплён вместе с SHA-256 для amd64 и arm64 в `vars/main.yml`.
Бинарник доступен только root в `/usr/local/lib/warp-native`. Регистрация
выполняется один раз с umask 0077. Аккаунт и исходный профиль хранятся на ноде в
`/var/lib/warp-native` (0700, файлы 0600), `/etc/wireguard/warp.conf` имеет 0600.
Секреты обрабатываются на ноде с `no_log` и без diff. Endpoint из профиля wgcf
разрешается строго в IPv4 и кэшируется при первой генерации; переменная endpoint
позволяет закрепить IPv4 явно. Её изменение сбрасывает кэш. Чтобы обновить DNS
принудительно, удалите `/var/lib/warp-native/endpoint.json` и примените роль снова.

## Переменные

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `warp_native_state` | `present` | Установка или `absent` для удаления |
| `warp_native_purge_account` | `false` | Удалить также сохранённый аккаунт при откате |
| `warp_native_watchdog_enabled` | `true` | Включить systemd timer |
| `warp_native_watchdog_interval` | `60` | Интервал после завершения проверки, минимум 30 секунд |
| `warp_native_watchdog_cooldown` | `180` | Пауза между попытками рестарта, минимум 120 секунд |
| `warp_native_probe_timeout` | `10` | Таймаут проверки, 2–30 секунд |
| `warp_native_endpoint` | `""` | Endpoint из профиля; можно задать IPv4/имя и порт |
| `warp_native_mtu` | `1280` | MTU, 1280–1420 |
| `warp_native_keepalive` | `25` | Keepalive, 0–65535 секунд |

Имена, метка и номер таблицы фиксированы. Watchdog делает HTTPS-запрос с меткой
и привязкой к `warp`, проверяет TLS и принимает только HTTP 200 с `warp=on`
или `warp=plus`. Ограничено время всего запроса. Старый handshake не означает
поломку. Неуспешный рестарт также расходует cooldown; дополнительно wg-quick
ограничен тремя запусками за десять минут.

## Зависимости

Пакеты Debian: `wireguard-tools`, `nftables`, `iproute2`, `ca-certificates`,
`python3`. Нужны systemd и ядро с WireGuard/nftables. Вызывающий play задаёт
`become: true`. Для чтения firewall даже в check mode нужен root, а для проверки
APT — `python3-apt`. Первый
check mode не регистрирует аккаунт и не создаёт профиль. Нет зависимостей от
Galaxy-ролей, warp-cli, SOCKS-демона, замены DNS или внешнего установщика.

## Пример подключения одной тестовой ноды

Из корня репозитория, с отдельным приватным inventory. `test` — имя из
примерного inventory; замените его на одну выбранную одноразовую ноду.

```bash
ansible-playbook -i ../infra-inventory/hosts.yml playbooks/warp-native.yml \
  -e warp_native_target=test --check --diff
ansible-playbook -i ../infra-inventory/hosts.yml playbooks/warp-native.yml \
  -e warp_native_target=test
ansible-playbook -i ../infra-inventory/hosts.yml playbooks/warp-native.yml \
  -e warp_native_target=test
```

Ожидается успешная проверка, установка и `changed=0` при втором реальном прогоне.
Это инструкция оператору: установка на нодах в рамках этой работы не выполнялась.
Playbook отклоняет групповые шаблоны и не включён в provisioning.

```bash
ansible -i ../infra-inventory/hosts.yml test -b -m ansible.builtin.command \
  -a 'systemctl status wg-quick@warp warp-native-guard warp-native-watchdog.timer --no-pager'
ansible -i ../infra-inventory/hosts.yml test -b -m ansible.builtin.command \
  -a 'nft list table inet warp_native'
ansible -i ../infra-inventory/hosts.yml test -b -m ansible.builtin.command \
  -a 'timeout 15 /usr/local/libexec/warp-native probe'
```

Ожидаются активные сервисы, одно правило drop для метки и код завершения probe
0. Probe не печатает адрес и секреты. `wg show warp` безопасен; `wg showconf`,
`wg show ... dump` и содержимое аккаунта/профиля содержат секреты.

## Xray и проверка трёх состояний

В [TESTING.md](TESTING.md) приведены готовый JSON, объяснение DNS, проверка
контейнера и точные команды для состояний WARP работает / остановлен /
восстановлен. В репозитории уже управляется создание профилей: опциональный
`profile_use_warp` теперь генерирует `ForceIPv4` и метку 51888. Это касается
только будущей генерации. Роль не обращается к API панели и не меняет живые
профили; `DIRECT` остаётся outbound по умолчанию без метки.

В изученном `docker-stacks/remnanode/docker-compose.yml` уже есть host network
и `cap_add: [NET_ADMIN]`: интерфейс хоста виден, capability для `SO_MARK`
предусмотрена. Фактические capabilities процесса Xray нужно проверить на
выбранной ноде. Сеть и capabilities Compose не изменялись.

## Обслуживание и откат

На выбранной тестовой ноде можно запретить watchdog, в том числе после reboot:

```bash
sudo touch /etc/warp-native/watchdog.disabled
sudo systemctl stop warp-native-watchdog.timer warp-native-watchdog.service
sudo systemctl stop wg-quick@warp
```

Ожидается остановленный интерфейс при сохранённых nft drop и unreachable route.
Для восстановления выполните `sudo rm -f /etc/warp-native/watchdog.disabled`,
затем `sudo systemctl start wg-quick@warp warp-native-watchdog.timer`.
Ожидается успешный probe. Через Ansible timer также отключается переменной
`warp_native_watchdog_enabled: false`; она не запрашивает удаление интерфейса.

Перед удалением уберите `warp-out` и его routing rules из тестового профиля,
проверьте отсутствие выбранного WARP-трафика, затем выполните:

```bash
ansible-playbook -i ../infra-inventory/hosts.yml playbooks/warp-native.yml \
  -e warp_native_target=test -e warp_native_state=absent
```

Ожидается удаление только сервисов роли, её drop-in, конфига интерфейса,
policy rule/маршрутов, nft-таблицы и исполняемых файлов. Аккаунт сохраняется для
повторной установки; для его удаления добавьте к этой команде
`-e warp_native_purge_account=true`. Общие пакеты, UFW/CrowdSec, resolver и
другие интерфейсы WireGuard не удаляются. Простое исключение роли из play
не удаляет уже установленное состояние.

## Поддерживаемые ОС

Debian 12 (bookworm) и 13 (trixie), amd64 / arm64, systemd.

Референсы и описание локальных тестов: [English README](README.md) и
[TESTING.md](TESTING.md).
