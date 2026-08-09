# Роль: common

[🇬🇧 English](README.md) · 🇷🇺 Русский

## Описание

Устанавливает настраиваемый список базовых пакетов, включает алгоритм
управления перегрузкой TCP BBR (вместе с qdisc `fq`) и настраивает **подкачку**
как сжатое в RAM устройство **zram** с диск-файлом-переливом низкого приоритета.
Некоторые образы провайдеров поставляются даже без `sudo`, `curl` и `wget` —
роль гарантирует, что на каждом хосте есть необходимый минимум. BBR — это отдача
от ядра XanMod (BBRv3); стоковые ядра Debian дают BBRv1, поэтому один и тот же
sysctl работает на всём флоте. На хосте с малой RAM подкачка сжимается **в RAM**
через zram (высокий приоритет) и в основном остаётся резидентной; маленький
диск-файл (низкий приоритет) ловит только настоящий перелив. Ядерный zswap
**отключён** — он ограничивает свой пул и проактивно пишет холодные страницы на
диск, и не уживается с zram — через живую запись в sysfs и cmdline ядра в GRUB
(`zswap.enabled=0`). Также включает реактивный TCP MTU probing, чтобы соединения
не зависали на путях, режущих ICMP, а восстанавливались, и тюнит лимиты обработки
соединений (SYN-очередь, эфемерные порты, потолок conntrack) под ноду с многими
одновременными клиентами. Идемпотентна.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `common_packages` | sudo, curl, wget, ca-certificates, gnupg, unzip, btop | Пакеты, которые должны быть установлены |
| `common_bbr_enabled` | `true` | Включить TCP BBR + qdisc `fq` через sysctl. `false` для ядра без BBR. |
| `common_tcp_mtu_probing` | `1` | `net.ipv4.tcp_mtu_probing`: 0 = выкл, 1 = реактивно (рекомендуется), 2 = всегда. |
| `common_tcp_max_syn_backlog` | `4096` | Размер очереди полуоткрытых соединений (`net.ipv4.tcp_max_syn_backlog`). |
| `common_ip_local_port_range` | `1024 65535` | Диапазон эфемерных портов для исходящих соединений. |
| `common_nf_conntrack_max` | `16384` | Потолок таблицы conntrack. `0` = оставить дефолт ядра и не загружать модуль (см. ниже). |
| `common_swap_enabled` | `true` | Общий выключатель всей настройки подкачки. |
| `common_zram_size` | `min(ram, 4096)` | Размер zram как выражение zram-generator (автомасштаб: `ram` = RAM хоста в МБ). Переопредели через `ram / 2` или литерал в МБ. |
| `common_zram_algo` | `zstd` | Алгоритм сжатия zram. |
| `common_zram_priority` | `100` | Приоритет zram-подкачки (выше диск-файла — заполняется первым). |
| `common_swapfile_path` | `/swapfile` | Путь диск-файла-перелива. |
| `common_swapfile_ram_multiplier` | `1` | Размер файла = RAM × это… |
| `common_swapfile_max_mb` | `1024` | …с жёстким потолком в MB (чтобы не разбух на диске). |
| `common_swapfile_priority` | `10` | Приоритет диск-файла (ниже zram — только перелив). |
| `common_zswap_disable` | `true` | Отключить ядерный zswap (sysfs сейчас + cmdline GRUB на ребуты). |
| `common_swappiness` | `150` | `vm.swappiness` — высокий, т.к. swap-in в zram дешёвый. |
| `common_page_cluster` | `0` | `vm.page-cluster` — отключить read-ahead подкачки (вреден для zram). |
| `common_watermark_boost_factor` | `0` | `vm.watermark_boost_factor`. |
| `common_watermark_scale_factor` | `125` | `vm.watermark_scale_factor` — раньше запускать reclaim. |

### Почему потолку conntrack нужен модуль, загруженный на старте

`systemd-sysctl` применяет `/etc/sysctl.d/` очень рано — раньше, чем что-либо
загрузит `nf_conntrack`. В этот момент `/proc/sys/net/netfilter/nf_conntrack_max`
не существует, строка молча пропускается, а юнит всё равно завершается с `0`,
потому что отсутствующий ключ для него не ошибка. Позже Docker поднимает
netfilter, модуль грузится, и ключ появляется с дефолтом ядра.

Внешним симптомом был вечный `changed` у задачи, при том что потолок оставался
дефолтным (#76). Поэтому роль пишет `/etc/modules-load.d/nf_conntrack.conf`,
который `systemd-modules-load.service` разбирает **до** запуска
`systemd-sysctl.service`, и загружает модуль для текущего прогона тоже.

## Зависимости

Нет.

## Пример

```yaml
- hosts: all
  become: true
  roles:
    - role: common
      vars:
        common_packages:
          - sudo
          - curl
          - git
```

## Поддерживаемые ОС

Debian 12/13, Ubuntu 22.04/24.04 (`os_family == 'Debian'`).
