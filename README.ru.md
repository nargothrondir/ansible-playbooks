# ansible-playbooks

[![Lint](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/lint.yml/badge.svg)](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/lint.yml)
[![Security](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/security.yml/badge.svg)](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/security.yml)
[![Molecule](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/molecule.yml/badge.svg)](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/molecule.yml)

[🇬🇧 English](README.md) · 🇷🇺 Русский

Личные Ansible-плейбуки для подготовки и обслуживания VPS.

## Стек

| Компонент | Детали |
|-----------|--------|
| ОС | Debian 12 → 13 на флоте, Ubuntu LTS на управляющем хосте |
| Ядро | XanMod (BBRv3) на нодах |
| DNS | systemd-resolved с DoT к выбранным апстримам (roles/dns) |
| Меш | NetBird — в него входит каждый хост; админ-поверхности доступны только через него |
| Контейнеры | Docker Engine + плагин Compose |
| Доставка контейнеров | Dockhand (стеки From-Git, опрос) с краевыми агентами Hawser |
| Автоматизация | Semaphore (веб-интерфейс Ansible) |
| Мониторинг | Beszel (агент + хаб), btop |
| Защита хоста | CrowdSec (детект по SSH, bouncer на nftables), ufw, доступ только по ключам |
| Секреты | OpenBao (runtime) · ansible-vault (наследие, выводится из обращения) |

## Роли

| Роль | Назначение | Зависит от |
|------|------------|------------|
| [bootstrap](roles/bootstrap/README.ru.md) | Создаёт пользователя `ansible` (только по ключу) и выдаёт беспарольный sudo | — |
| [apt_sources](roles/apt_sources/README.ru.md) | Один канонический deb822-файл источников архива Debian вместо того, что положил образ провайдера (только Debian) | — |
| [dns](roles/dns/README.ru.md) | Шифрованный DNS для собственных запросов хоста: systemd-resolved + DoT, серверы интерфейса убраны, чтобы настройка действовала | — |
| [common](roles/common/README.ru.md) | Установка базовых пакетов (sudo, curl, wget, ...) | — |
| [docker](roles/docker/README.ru.md) | Docker Engine + Compose-плагин из официального репозитория | — |
| [xanmod](roles/xanmod/README.ru.md) | Установка производительного ядра XanMod | — |
| [netbird](roles/netbird/README.ru.md) | Установка агента NetBird и вступление в меш | — |
| [ufw](roles/ufw/README.ru.md) | Host-файрвол: публичные 22/443, сервисные порты только с wt0 | — |
| [ssh_hardening](roles/ssh_hardening/README.ru.md) | Mesh-only порт sshd (2200) для автоматизации по ключу | ufw |
| [crowdsec](roles/crowdsec/README.ru.md) | Детект только по SSH с прогрессивными банами, nftables-баунсер; проводка к центральному LAPI заложена (неактивна) | common |
| [upgrade](roles/upgrade/README.ru.md) | `apt update` + `full-upgrade` + `autoremove`, перезагрузка при необходимости | — |
| [notify_telegram](roles/notify_telegram/README.ru.md) | Отправка сообщения в Telegram-чат через Bot API | — |
| [semaphore](roles/semaphore/README.ru.md) | Развёртывание Semaphore (веб-UI для Ansible) через Docker Compose | — |
| [dockhand](roles/dockhand/README.ru.md) | Развёртывание Dockhand (веб-UI для Docker) через Docker Compose | — |
| [hawser](roles/hawser/README.ru.md) | Развёртывание edge-агента Hawser (для Dockhand) на хосте | — |
| [beszel_agent](roles/beszel_agent/README.ru.md) | Агент мониторинга Beszel (бинарник + systemd, WebSocket к хабу, без входящего порта) | — |
| [openbao](roles/openbao/README.ru.md) | Хранилище секретов OpenBao (встроенный Raft) на хосте панели; init и unseal остаются ручными | — |

## Плейбуки

| Плейбук | Роли | Целевая группа |
|---------|------|----------------|
| [playbooks/site.yml](playbooks/site.yml) | bootstrap (под root), upgrade (под `ansible`) | new_vps |
| [playbooks/update.yml](playbooks/update.yml) | upgrade + notify_telegram (отчёт) | managed |
| [playbooks/semaphore.yml](playbooks/semaphore.yml) | semaphore | `semaphore_target` (по умолчанию: panel) |
| [playbooks/dockhand.yml](playbooks/dockhand.yml) | dockhand | `dockhand_target` (по умолчанию: panel) |
| [playbooks/hawser.yml](playbooks/hawser.yml) | hawser (хосты с токеном) | managed |
| [playbooks/provision.yml](playbooks/provision.yml) | common, docker | lab |
| [playbooks/dns.yml](playbooks/dns.yml) | dns (шифрованный резолвер) | `dns_target` (по умолчанию: lab) |
| [playbooks/apt-sources.yml](playbooks/apt-sources.yml) | apt_sources (канонические источники архива Debian) | `apt_sources_target` (по умолчанию: lab) |
| [playbooks/common.yml](playbooks/common.yml) | common (повторное применение базовой роли) | `common_target` (по умолчанию: lab) |
| [playbooks/crowdsec.yml](playbooks/crowdsec.yml) | crowdsec | fleet (кроме panel) |
| [playbooks/beszel.yml](playbooks/beszel.yml) | beszel_agent | fleet (кроме panel) |
| [playbooks/provision-node.yml](playbooks/provision-node.yml) | bootstrap, upgrade, ssh_hardening, common, dns, netbird, docker, xanmod, hawser, crowdsec, ufw, beszel_agent + API панели | (survey) |
| [playbooks/new-profile.yml](playbooks/new-profile.yml) | — (вызов API панели) | control |
| [playbooks/new-node.yml](playbooks/new-node.yml) | — (вызов API панели) | control |
| [playbooks/dns-record.yml](playbooks/dns-record.yml) | — (API Cloudflare; импортируется provision-node.yml или отдельно) | `dns_target` (по умолчанию: controller) |
| [playbooks/dockhand-environment.yml](playbooks/dockhand-environment.yml) | — (API Dockhand через панель; импортируется provision-node.yml или отдельно) | `dockhand_env_target` (по умолчанию: controller) |
| [playbooks/dockhand-stack.yml](playbooks/dockhand-stack.yml) | — (API Dockhand и панели через панель; разворачивает From-Git стек ноды) | `dockhand_stack_target` (по умолчанию: controller) |
| [playbooks/semaphore-template.yml](playbooks/semaphore-template.yml) | — (вызов API Semaphore; создаёт недостающие шаблоны задач, существующие не меняет) | `semaphore_template_target` (по умолчанию: controller) |
| [playbooks/semaphore-survey.yml](playbooks/semaphore-survey.yml) | — (вызов API Semaphore) | control |
| [playbooks/semaphore-inventory-repo.yml](playbooks/semaphore-inventory-repo.yml) | — (вызов API Semaphore; без аргументов только отчёт) | control |
| [playbooks/openbao.yml](playbooks/openbao.yml) | openbao | `openbao_target` (default: panel) |
| [playbooks/openbao-setup.yml](playbooks/openbao-setup.yml) | — (API OpenBao: KV, политика, AppRole; запуск с CLI панели с коротким токеном) | `openbao_setup_target` (по умолчанию: panel) |
| [playbooks/openbao-verify.yml](playbooks/openbao-verify.yml) | — (проверяет цепочку AppRole → чтение KV; запускать из Semaphore) | `openbao_verify_target` (по умолчанию: controller) |
| [playbooks/mesh-ssh-check.yml](playbooks/mesh-ssh-check.yml) | — (проверка SSH через меш) | control → mesh-пиры |

## Скрипты

| Скрипт | Назначение |
|---|---|
| [scripts/verify-secret-migration.py](scripts/verify-secret-migration.py) | Сверяет каждый секрет ansible-vault с его двойником в OpenBao. **Запускать перед удалением vault-файлов** (#2, #7). Печатает только имена и вердикты — значения сравниваются усечёнными хешами. |

## Инвентарь

**Инвентаря в этом репозитории нет.** Адреса хостов, адреса меша, домены
сервисов и публичные SSH-ключи идентифицируют конкретные машины, поэтому они
живут в приватном репозитории, а этот остаётся пригодным к публикации.
Структура задокументирована в
[inventory/hosts.example.yml](inventory/hosts.example.yml); в CI работает
`.github/scripts/tells-guard.sh` и роняет сборку, если адрес или неизвестный
домен появится здесь снова.

Semaphore подключает приватный инвентарь отдельной записью Repository, не той
же, что этот репозиторий. Для локального прогона склонируйте его рядом с этим
чекаутом и укажите путь явно — `group_vars/` и `host_vars/` обязаны оставаться
соседями файла инвентаря, потому что Ansible ищет их относительно него, а при
уплощённой раскладке все переменные **молча** становятся неопределёнными:

```bash
ansible-playbook -i ../infra-inventory/hosts.yml playbooks/site.yml
```

| Группа | Назначение |
|--------|------------|
| new_vps | Только что развёрнутые серверы до bootstrap |
| managed | Подготовленные хосты, управляемые через пользователя `ansible` |
| control | Сам управляющий узел Ansible (локальное подключение) |
| lab | Экспериментальные/одноразовые хосты (без ежедневных обновлений) |

## Модель аутентификации

Аутентификация **только по ключу**, **отдельный ключ на каждую identity**
(нельзя делить один ключ между пользователями), паролей нигде не хранится:

- **root** доступен по вашему **админскому** ключу — только для первичного
  bootstrap. Вставьте его публичную часть в root при создании VPS (UI
  провайдера / cloud-init) либо один раз скопируйте:
  `ssh-copy-id -i ~/.ssh/admin_ed25519.pub root@<host>`.
- Пользователь **`ansible`** получает **выделенный ключ автоматизации**
  (авторизуется ролью bootstrap), его пароль заблокирован. Этим ключом идут
  все последующие прогоны.

Runtime-секреты живут в **OpenBao**: его разворачивает роль `openbao` на
управляющем хосте, а плейбуки читают их через AppRole. Файлы `ansible-vault` в
приватном инвентаре — остаток прежней схемы, они выводятся из обращения.
Управляющая машина должна быть на Linux или WSL — Ansible не работает на
нативном Windows.

## Использование

1. Подготовьте два ключа (админский можно взять из существующего личного):

   ```bash
   # админский ключ для доступа к root (пропустите, если личный ключ уже есть)
   ssh-keygen -t ed25519 -a 100 -f ~/.ssh/admin_ed25519 -C "admin@controller"
   # выделенный ключ автоматизации для пользователя ansible
   ssh-keygen -t ed25519 -a 100 -f ~/.ssh/ansible_ed25519 -C "ansible@controller"
   ```

2. Убедитесь, что root принимает ваш **админский** публичный ключ: вставьте его
   при создании VPS либо выполните один раз
   `ssh-copy-id -i ~/.ssh/admin_ed25519.pub root@<host>`.
3. Впишите **публичный** ключ `ansible` в `bootstrap_authorized_keys` в
   `group_vars/new_vps.yml` **приватного репозитория с инвентарём**.
4. Добавьте целевые хосты в группу `new_vps` в его `hosts.yml`.
5. Загрузите ключи в ssh-agent и запустите процесс (пути к приватным ключам в
   гите не хранятся):

   ```bash
   ssh-add ~/.ssh/admin_ed25519 ~/.ssh/ansible_ed25519
   ansible-playbook playbooks/site.yml
   ```

Первый play подключается под `root` (админский ключ) и создаёт пользователя
`ansible` (только по ключу) с sudo; второй play переподключается **под
`ansible`** (ключ автоматизации) и обновляет сервер, перезагружая его только
когда работающее ядро перестало быть новейшим установленным (`needrestart -b
-k`, плюс маркер `/var/run/reboot-required` там, где его создаёт Ubuntu).

### Плановые обновления с отчётом в Telegram

[playbooks/update.yml](playbooks/update.yml) обновляет хосты группы `managed` и
шлёт один сводный отчёт в Telegram с контроллера. Данные бота — через
ansible-vault:

```bash
# в приватном репозитории с инвентарём
ansible-vault create group_vars/all/vault.yml
# vault_telegram_bot_token: "123456:ABC-..."
# vault_telegram_chat_id: "123456789"

ansible-playbook -i ../infra-inventory/hosts.yml playbooks/update.yml --ask-vault-pass
```

## Спецификация агента

Репозиторий следует строгой спецификации AI-агента — см.
[`CLAUDE.md`](./CLAUDE.md) (v4.0: компактное ядро + детали по запросу в
[`references/`](references/)). Каталог `.skill/` упаковывает её как скилл
для Claude Desktop; см. [`.skill/README.md`](./.skill/README.md).

Журнал разработки: [`OBSERVATIONS.md`](./OBSERVATIONS.md) · план развития:
[`ROADMAP.md`](./ROADMAP.md).

### Субагенты

В `.claude/agents/` описаны четыре узких помощника на более дешёвой модели.
Им делегируется работа, результат которой **дёшево проверить**, и никогда —
работа, порождающая суждение:

| Агент | Что делает | Что возвращает |
|-------|------------|----------------|
| `repo-scout` | поиск по репозиторию только на чтение (проверки зависимостей §3) | доказательства `file:line` |
| `run-triage` | структурирует длинный вывод Ansible/CI/диагностики | падения по хостам, recap, флаги |
| `claim-checker` | проверяет утверждение до того, как его записали | CONFIRMED / REFUTED / UNVERIFIABLE + цитата |
| `upstream-facts` | добывает факты из внешней документации и релизов | цитаты со ссылками |

Всё детерминированное вместо этого идёт в CI — см.
[`.github/scripts/spec-guards.sh`](.github/scripts/spec-guards.sh).

## Авторы

- [nargothrondir](https://github.com/nargothrondir) — автор и мейнтейнер
- Создано в паре с **Claude** (Anthropic) как AI-ассистентом — см.
  трейлеры `Co-Authored-By` в истории git.

## Структура

```
ansible-playbooks/
├── CLAUDE.md               # спецификация AI-агента (источник истины)
├── references/             # детали спецификации, читаются по запросу
├── .claude/agents/         # узкие субагенты (дешёвая модель, проверяемый вывод)
├── ROADMAP.md              # планируемые улучшения спецификации
├── OBSERVATIONS.md         # журнал наблюдений за поведением агента
├── inventory/
│   └── hosts.example.yml   # только структура — реальный инвентарь приватен
├── roles/                  # 15 ролей, у каждой пара README (см. таблицу выше)
├── playbooks/
│   ├── tasks/              # переиспользуемые файлы задач (например чтение OpenBao)
│   └── templates/          # шаблоны, которые рендерят плейбуки
├── scripts/                # инструменты оператора, вне прогонов
├── requirements.yml        # запиненные коллекции
├── ansible.cfg
├── .ansible-lint
├── .github/
│   ├── workflows/          # lint · security · guards · molecule · ci-alert
│   └── scripts/            # spec-guards.sh · tells-guard.sh
└── .skill/                 # скилл для Claude Desktop (зеркало CLAUDE.md)
```

Номера issue в комментариях (`#122`, `#68`) указывают на трекер проекта,
который не публичен: этот репозиторий опубликован снимком без истории, а
бэклог остался в приватном предшественнике — его issue содержат адреса и
скриншоты. Они сохранены как происхождение решения, которое комментарий
объясняет, а не как ссылки, по которым можно перейти.

Новые issue заводятся там же, чтобы разделение не размывалось со временем.
Трекер этого репозитория оставлен для того, что заводят снаружи.
