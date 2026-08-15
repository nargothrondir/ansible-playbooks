# Роль: apt_sources

[🇬🇧 English](README.md) · 🇷🇺 Русский

## Описание

Записывает источники архива Debian в один канонический deb822-файл и убирает всё,
что положил образ провайдера. Сторонние репозитории не трогает — ими владеют
`roles/docker`, `roles/netbird`, `roles/xanmod` и `roles/crowdsec`.

## Зачем

Флот собран из пяти образов разных провайдеров, и каждый разложил apt по-своему.
Измерено на всех пяти нодах 2026-08-14:

| | раскладка | схема | компоненты | security | backports |
|---|---|---|---|---|---|
| A | `sources.list` | http | `main non-free-firmware` | `security.debian.org/debian-security` | нет |
| B | `sources.list` | http | `main non-free-firmware` | `deb.debian.org/debian-security` | нет |
| C | `sources.list` | https | `main contrib non-free non-free-firmware` | `security.debian.org/debian-security` | нет |
| D | фрагменты в `sources.list.d/` | http | `main` | `security.debian.org/` | **да** |
| E | `debian.sources` (deb822) | https | — | `deb.debian.org/debian-security` | нет |

Ни одна не смотрела на зеркало хостера — а это было исходное опасение. Настоящая
проблема оказалась у́же и неприятнее: **один и тот же `apt install` мог пройти на
одной ноде и не найти пакет на другой**, потому что где-то были `contrib` и
`non-free`, а где-то только `main`.

## Что делает

- пишет `/etc/apt/sources.list.d/debian.sources` — https, `main
  non-free-firmware`, безопасность с `security.debian.org/debian-security`
- удаляет `/etc/apt/sources.list` и любой файл в `sources.list.d/`, указывающий
  на архив Debian
- сначала делает резервные копии всего удаляемого, с суффиксом, который apt не
  читает
- обновляет списки пакетов и **спрашивает у apt**, что он теперь тянет

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `apt_sources_uri` | `https://deb.debian.org/debian` | Основной архив |
| `apt_sources_security_uri` | `https://security.debian.org/debian-security` | Архив безопасности — свой хост и канонический путь |
| `apt_sources_components` | `main non-free-firmware` | `contrib`/`non-free` намеренно отсутствуют: на флоте оттуда ничего не установлено |
| `apt_sources_backports` | `false` | При `true` добавляет `<suite>-backports` |
| `apt_sources_suite` | `{{ ansible_distribution_release }}` | Берётся с хоста — зашитое имя релиза ломается на следующем |
| `apt_sources_file` | `/etc/apt/sources.list.d/debian.sources` | Куда пишется канонический файл |
| `apt_sources_keyring` | `/usr/share/keyrings/debian-archive-keyring.gpg` | `Signed-By` для обеих строф |
| `apt_sources_backup_suffix` | `.pre-apt-sources.bak` | apt читает только `*.list` и `*.sources`, поэтому копии могут лежать рядом |
| `apt_sources_require_debian` | `true` | Отказывается работать на Ubuntu, где другой архив и другие имена компонентов |

## Два решения, о которых стоит знать

**https, а не http.** Подписи защищают целостность в обоих случаях — это позиция
самого Debian и причина, почему http до сих пор дефолт. https дополнительно
скрывает от наблюдателя, **какие именно** пакеты тянет хост, а одна нода флота
стоит за блокировками.

**deb822, а не однострочный формат.** Причина — `Signed-By`. В deb822 это поле, в
однострочном — опция в скобках, которую легко забыть. А забытый `Signed-By`
означает, что apt проверяет этот репозиторий по **любому** ключу из доверенного
набора: именно так сторонний репозиторий незаметно становится доверенным наравне
с самим Debian.

## Сопоставление по содержимому, а не по имени

Удаляемые файлы находятся по URI архива Debian внутри них, потому что имена у
каждого образа свои: `sources.list`, `default.list`, `updates.list`,
`security.list`, `debian.sources`. Сторонние репозитории указывают на
`download.docker.com`, `pkgs.netbird.io`, `deb.xanmod.org` и `packagecloud.io` —
совпасть не могут и не трогаются никогда.

Файлы меньше двух байт тоже удаляются: в них не помещается `deb URI suite
component`, то есть они ничего не объявляют. Один образ оставил однобайтовый файл
с именем `.list`.

## Проверка идёт у apt, а не по файлам

После записи роль спрашивает `apt-get indextargets`, что apt будет тянуть на
самом деле, и падает, если появляется архив Debian, которого она не объявляла.
Написать верный файл и быть единственным файлом — разные вещи: на нескольких
нодах правдоподобный `sources.list` лежал рядом с `sources.list.d/`, который тоже
читался, а apt берёт объединение.

## Зависимости

Нет. Только Debian — ассерт не даст запуститься в другом месте.

## Пример

```yaml
- name: Normalise apt sources
  hosts: lab
  become: true
  roles:
    - apt_sources
```

## Поддерживаемые ОС

Debian 12 (bookworm), Debian 13 (trixie). **Не Ubuntu** — управляющий хост
сознательно вне области действия, и ассерт это обеспечивает.
