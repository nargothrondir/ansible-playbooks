# Role: common

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Installs a configurable list of baseline packages, enables the TCP BBR
congestion control algorithm (with the `fq` qdisc), and sets up **swap** as a
**zram** compressed-RAM device backed by a low-priority disk file. Some provider
images ship without even `sudo`, `curl` or `wget` — this role guarantees every
host has the essentials. BBR is the payoff of the XanMod kernel (BBRv3); stock
Debian kernels provide BBRv1, so the same sysctl applies fleet-wide. On a RAM-
tight host, swap is compressed **in RAM** by zram (high priority) so most of it
stays resident; a small disk file (low priority) catches only true overflow. The
kernel's zswap is **disabled** — it caps its pool and proactively writes cold
pages to disk, and it cannot coexist with zram — via a live sysfs write and the
GRUB cmdline (`zswap.enabled=0`). Also enables reactive TCP MTU probing so
connections recover instead of stalling on paths that drop ICMP, and tunes
connection-handling limits (SYN backlog, ephemeral ports, conntrack cap) for a
node serving many concurrent clients. Idempotent.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `common_packages` | sudo, curl, wget, ca-certificates, gnupg, unzip, btop | Packages to ensure are installed |
| `common_bbr_enabled` | `true` | Enable TCP BBR + `fq` qdisc via sysctl. Set `false` for a kernel without BBR. |
| `common_tcp_mtu_probing` | `1` | `net.ipv4.tcp_mtu_probing`: 0 = off, 1 = reactive (recommended), 2 = always. |
| `common_tcp_max_syn_backlog` | `4096` | Half-open (SYN) queue size (`net.ipv4.tcp_max_syn_backlog`). |
| `common_ip_local_port_range` | `1024 65535` | Ephemeral port range for outbound connections. |
| `common_nf_conntrack_max` | `16384` | conntrack table cap. `0` = leave the kernel default, and skips the module-load below. |
| `common_swap_enabled` | `true` | Master switch for all swap configuration. |
| `common_zram_size` | `min(ram, 4096)` | zram size as a zram-generator expression (auto-scales: `ram` = host RAM in MB). Override with `ram / 2` or a literal MB. |
| `common_zram_algo` | `zstd` | zram compression algorithm. |
| `common_zram_priority` | `100` | zram swap priority (higher than the disk file, so it fills first). |
| `common_swapfile_path` | `/swapfile` | Path of the disk overflow swap file. |
| `common_swapfile_ram_multiplier` | `1` | Swap-file size = RAM × this… |
| `common_swapfile_max_mb` | `1024` | …hard-capped at this many MB (keeps it off the disk). |
| `common_swapfile_priority` | `10` | Disk swap-file priority (below zram — overflow only). |
| `common_zswap_disable` | `true` | Disable the kernel zswap (sysfs now + GRUB cmdline for reboots). |
| `common_swappiness` | `150` | `vm.swappiness` — high, since zram swap-in is cheap. |
| `common_page_cluster` | `0` | `vm.page-cluster` — disable swap read-ahead (harmful for zram). |
| `common_watermark_boost_factor` | `0` | `vm.watermark_boost_factor`. |
| `common_watermark_scale_factor` | `125` | `vm.watermark_scale_factor` — start reclaim earlier. |

### Why the conntrack cap needs the module loaded at boot

`systemd-sysctl` applies `/etc/sysctl.d/` very early — before anything loads
`nf_conntrack`. At that point `/proc/sys/net/netfilter/nf_conntrack_max` does
not exist, so the line is skipped, and the unit still exits `0` because a
missing key is not an error to it. Docker brings netfilter up later, the module
loads, and the key appears holding the kernel default.

The visible symptom was a task reporting `changed` on every single run while
the cap stayed at the default (#76). The role therefore writes
`/etc/modules-load.d/nf_conntrack.conf`, which `systemd-modules-load.service`
consumes **before** `systemd-sysctl.service` runs, and loads the module for the
current run as well.

## Dependencies

None.

## Example

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

## Supported OS

Debian 12/13, Ubuntu 22.04/24.04 (`os_family == 'Debian'`).
