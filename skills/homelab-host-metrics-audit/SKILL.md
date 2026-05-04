---
name: homelab-host-metrics-audit
description: >-
  Audits homelab host resource health using Grafana Prometheus/Mimir/Thanos
  metrics, especially node-exporter style system metrics. Covers host coverage,
  scrape health, CPU saturation, load, memory and swap pressure, filesystem
  capacity and inode exhaustion, disk I/O latency/saturation, network errors,
  reboots, clock drift, RAID/ZFS/storage health when exported, and human
  intervention thresholds. Use when the user asks to check all hosts for system
  metrics pressure, resource exhaustion, capacity risk, or Prometheus-based
  host health in Grafana.
---

# Homelab Host Metrics Audit

Use this skill to answer: "Are any hosts under resource pressure and do they need human intervention?" Prefer facts from Prometheus metrics over guesses from logs. This complements Loki host/container log audits: metrics show pressure and trends; logs explain why.

## Baseline workflow

1. **Time range** - Use an explicit range, usually last 1h for current pressure and last 24h or 7d for capacity trends.
2. **Datasource discovery** - In Grafana MCP, run `list_datasources` with `type: prometheus` and use the returned `uid`. Mimir/Thanos/Cloud Monitoring datasources may still accept PromQL through the Prometheus tools.
3. **Metric discovery** - Confirm the local exporter schema before judging health:
   - `list_prometheus_metric_names` with regex `^(up|node_.*)$`
   - `list_prometheus_label_values` for `job` and `instance`
   - If present, check `nodename` from `node_uname_info`.
4. **Coverage check** - Identify expected hosts, missing hosts, scrape failures, and stale targets.
5. **Pressure pass** - Run CPU/load, memory/swap, filesystem, disk I/O, network, reboot/time, and hardware/storage checks.
6. **Trend pass** - For capacity, inspect 24h/7d maxima and free-space slope, not only the current value.
7. **Triage** - Assign severity using the guidance below and recommend concrete actions.
8. **Report** - Use the findings format at the end.

## Using Grafana MCP

- `list_datasources` with `type: prometheus` -> use returned `uid`.
- `list_prometheus_metric_names` -> discover whether node exporter metrics exist.
- `list_prometheus_label_values` -> discover `job`, `instance`, `device`, `mountpoint`, `fstype`, and `nodename` values.
- `query_prometheus` -> run instant or range PromQL with `datasourceUid`, `expr`, `queryType`, `startTime`, `endTime`, and `stepSeconds`.

Start with instant queries for a snapshot, then use range queries for trend-sensitive findings. Do not rely on a single spike unless it is severe or sustained.

## Label conventions

Node exporter commonly uses:

- `job` - scrape job, often `node`, `node-exporter`, or host-specific.
- `instance` - scrape target, often `host:9100`.
- `nodename` - real hostname exposed by `node_uname_info`, if joined into queries.
- `device`, `mountpoint`, `fstype` - filesystem and block device dimensions.

If `nodename` is available, add it to host reports by joining with `node_uname_info`:

```promql
<query> * on(instance) group_left(nodename) node_uname_info
```

If that join produces errors or duplicate series, report by `instance` and mention the label mismatch.

## Coverage and scrape health

Run these before saying the fleet is healthy.

| Concern | Example PromQL |
|--------|----------------|
| Targets down now | `up{job=~".*node.*"} == 0` |
| Targets with scrape gaps in last hour | `max_over_time(up{job=~".*node.*"}[1h]) < 1` |
| Hosts seen via node exporter | `count by (instance) (node_uname_info)` |
| Exporter restarts / host reboot signal | `time() - node_boot_time_seconds` |
| Scrape duration near timeout | `scrape_duration_seconds{job=~".*node.*"} / scrape_timeout_seconds{job=~".*node.*"} > 0.8` |
| Node exporter absent from expected host | Compare expected inventory to `instance` / `nodename` values |

If `job=~".*node.*"` misses local metrics, discover `job` values and substitute the actual job selector.

## CPU and load pressure

| Concern | Example PromQL | Human threshold |
|--------|----------------|-----------------|
| CPU busy percentage | `100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))` | Sustained > 90% is High; > 95% with service impact is Critical |
| I/O wait percentage | `100 * avg by (instance) (rate(node_cpu_seconds_total{mode="iowait"}[5m]))` | Sustained > 10% Medium; > 20% High |
| Steal time on virtual hosts | `100 * avg by (instance) (rate(node_cpu_seconds_total{mode="steal"}[5m]))` | Sustained > 5% Medium; > 15% High |
| Load per CPU | `node_load15 / count by (instance) (node_cpu_seconds_total{mode="idle"})` | Sustained > 1.5 Medium; > 2 High |
| CPU saturation trend | `max_over_time((100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))))[1h:5m])` | Use to distinguish spike from sustained pressure |

Prefer 5m rates for current state and 1h max/avg for severity. High CPU alone may be normal for batch workloads; raise severity when paired with load, latency, iowait, OOM, or user-facing impact.

## Memory and swap pressure

| Concern | Example PromQL | Human threshold |
|--------|----------------|-----------------|
| Memory available percentage | `100 * node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes` | < 10% Medium; < 5% High; < 2% Critical |
| Swap used percentage | `100 * (node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes) / node_memory_SwapTotal_bytes` | > 25% Medium; > 50% High if growing |
| Swap-in rate | `rate(node_vmstat_pswpin[5m])` | Sustained non-zero with low memory is High |
| Swap-out rate | `rate(node_vmstat_pswpout[5m])` | Sustained non-zero with low memory is High |
| Major page faults | `rate(node_vmstat_pgmajfault[5m])` | Rising with latency/OOM symptoms is Medium/High |
| OOM kills if exported | `increase(node_vmstat_oom_kill[1h])` | Any value > 0 is High |

If `SwapTotal` is zero, avoid divide-by-zero findings. Treat no-swap hosts as higher risk when memory available is very low.

## Filesystem capacity and inodes

Exclude pseudo and temporary filesystems unless the local environment needs them:

```promql
fstype!~"tmpfs|devtmpfs|overlay|squashfs|proc|sysfs|cgroup2?|nsfs|autofs|tracefs|debugfs|securityfs|fuse.lxcfs|ramfs"
```

| Concern | Example PromQL | Human threshold |
|--------|----------------|-----------------|
| Filesystem used percentage | `100 * (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|devtmpfs|overlay|squashfs"} / node_filesystem_size_bytes{fstype!~"tmpfs|devtmpfs|overlay|squashfs"})` | > 85% Medium; > 90% High; > 95% Critical |
| Free bytes | `node_filesystem_avail_bytes{fstype!~"tmpfs|devtmpfs|overlay|squashfs"}` | Critical if root or data volume has too little headroom for normal writes |
| Inode used percentage | `100 * (1 - node_filesystem_files_free{fstype!~"tmpfs|devtmpfs|overlay|squashfs"} / node_filesystem_files{fstype!~"tmpfs|devtmpfs|overlay|squashfs"})` | > 85% Medium; > 90% High; > 95% Critical |
| Read-only filesystem | `node_filesystem_readonly{fstype!~"tmpfs|devtmpfs|overlay|squashfs"} == 1` | Critical for writable system/data mounts |
| 24h capacity peak | `max_over_time((100 * (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|devtmpfs|overlay|squashfs"} / node_filesystem_size_bytes{fstype!~"tmpfs|devtmpfs|overlay|squashfs"}))[24h:15m])` | Use for trend/capacity warning |

Prioritize `/`, `/var`, Docker/container storage, database volumes, media/download volumes, backup targets, and monitoring storage. A full non-critical read-only ISO mount is noise.

## Disk I/O and block device pressure

Device names vary. Exclude loop, ram, and optical devices unless relevant:

```promql
device!~"loop.*|ram.*|fd.*|sr.*"
```

| Concern | Example PromQL | Human threshold |
|--------|----------------|-----------------|
| Disk utilization approximation | `100 * rate(node_disk_io_time_seconds_total{device!~"loop.*|ram.*|fd.*|sr.*"}[5m])` | Sustained > 80% Medium; > 95% High |
| Read latency approximation | `rate(node_disk_read_time_seconds_total{device!~"loop.*|ram.*|fd.*|sr.*"}[5m]) / rate(node_disk_reads_completed_total{device!~"loop.*|ram.*|fd.*|sr.*"}[5m])` | Rising or > 50ms needs review; > 200ms High |
| Write latency approximation | `rate(node_disk_write_time_seconds_total{device!~"loop.*|ram.*|fd.*|sr.*"}[5m]) / rate(node_disk_writes_completed_total{device!~"loop.*|ram.*|fd.*|sr.*"}[5m])` | Rising or > 50ms needs review; > 200ms High |
| Disk queued I/O | `rate(node_disk_io_time_weighted_seconds_total{device!~"loop.*|ram.*|fd.*|sr.*"}[5m])` | High relative to baseline with iowait indicates pressure |
| Disk I/O errors if exported | Search metric names for `disk.*error`, `smart`, `nvme`, `ata`, `zfs`, `md` | Any confirmed hardware/storage error is High |

Division by zero may produce no data or `NaN`; ignore idle devices. If disk pressure appears, correlate with filesystem fullness, backups, databases, media indexing, and Loki logs.

## Network pressure and errors

Exclude virtual interfaces when they are noisy and not useful:

```promql
device!~"lo|docker.*|veth.*|br-.*|cni.*|flannel.*|tailscale.*"
```

| Concern | Example PromQL | Human threshold |
|--------|----------------|-----------------|
| Receive error rate | `rate(node_network_receive_errs_total{device!~"lo|docker.*|veth.*|br-.*"}[5m])` | Sustained non-zero on physical NIC is Medium/High |
| Transmit error rate | `rate(node_network_transmit_errs_total{device!~"lo|docker.*|veth.*|br-.*"}[5m])` | Sustained non-zero on physical NIC is Medium/High |
| Receive drops | `rate(node_network_receive_drop_total{device!~"lo|docker.*|veth.*|br-.*"}[5m])` | Sustained drops need review |
| Transmit drops | `rate(node_network_transmit_drop_total{device!~"lo|docker.*|veth.*|br-.*"}[5m])` | Sustained drops need review |
| Link flaps if exported | `changes(node_network_carrier{device!~"lo|docker.*|veth.*|br-.*"}[1h])` | Any repeated physical NIC flap is High |

Do not call high throughput pressure without knowing link speed. If link speed metrics exist, compare bytes/sec to capacity; otherwise report errors/drops/flaps, not utilization percentage.

## Reboots, time, and system health

| Concern | Example PromQL | Human threshold |
|--------|----------------|-----------------|
| Recent reboot | `time() - node_boot_time_seconds < 3600` | Medium unless expected; High if repeated or correlated with failures |
| Repeated reboot in range | `changes(node_boot_time_seconds[24h]) > 0` | High if unexpected |
| Time sync offset if exported | Search for `node_timex_offset_seconds` or `ntp` metrics | > 1s Medium; > 5s High for distributed systems |
| File descriptor exhaustion | `100 * node_filefd_allocated / node_filefd_maximum` | > 80% Medium; > 90% High |
| Process/thread exhaustion if exported | Search metric names for `processes`, `threads`, `forks` | High when near kernel/user limits |

## Hardware and storage-health exporters

If present, inspect these metric families:

- SMART exporter: `smartmon_*`, `smartctl_*`
- NVMe exporter: `nvme_*`
- mdraid exporter: `node_md_*`, `mdadm_*`
- ZFS exporter: `node_zfs_*`, `zfs_*`
- UPS exporter: `nut_*`, `ups_*`
- Thermal sensors: `node_hwmon_*`, `temperature_*`

Treat failed disks, degraded arrays, high media error counts, read-only pools, critical temperatures, and UPS-on-battery with low charge as High or Critical depending on redundancy and service impact.

## Correlation checks

- CPU saturation + load per CPU > 2 + user-facing errors or latency.
- Low memory + swap-in/out + OOM kills or app restarts.
- High iowait + disk utilization + filesystem near full.
- Filesystem near full + Loki/container logs showing write failures.
- Network drops/errors + service timeouts or DNS/upstream errors.
- Recent reboot + host logs showing kernel panic, OOM, power loss, or failed units.
- One shared storage/network dependency causing pressure on multiple hosts.

## Findings format

Produce a short report:

```markdown
## Grafana Prometheus host metrics audit (<time range>)

### Summary
- Datasource: ...
- Host metric selector: ...
- Hosts reporting: ...
- Expected hosts missing: ...
- Overall status: Healthy / Watch / Intervention needed

### Intervention findings
- **<Severity> - <finding title>**
  - Host: ...
  - Metric(s): ...
  - Current / peak: ...
  - Time window: ...
  - Why it matters: ...
  - Suggested action: ...

### Watchlist
- Hosts/resources close to threshold but not yet urgent.

### Coverage gaps
- Missing exporters, stale hosts, absent metric families, or label/schema limits.

### Follow-ups
- Alerts to add, dashboards to check, logs to correlate, or capacity tasks.
```

**Severity guidance:** Critical (resource exhaustion causing outage or imminent data loss: read-only root/data filesystem, >95% critical mount, OOM kills with service impact, degraded storage without redundancy, host down, severe thermal/power event). High (sustained CPU/load/iowait/memory/swap pressure, >90% critical filesystem/inodes, repeated reboots, physical NIC errors/flaps, storage errors). Medium (near-capacity >85%, intermittent pressure, single unexpected reboot, scrape instability, moderate network drops, swap use without clear impact). Low (short spikes, non-critical mounts, expected maintenance, noisy virtual interfaces).

Raise severity when pressure is sustained, affects multiple hosts, involves root/data/monitoring storage, correlates with errors or restarts, or has no obvious maintenance explanation. Lower severity for known batch jobs, backups, expected reboots, temporary removable filesystems, and virtual network interfaces.

## Important caveats

- Prometheus label schemas vary. Discover metric names and labels before running fixed queries.
- Node exporter does not expose every hardware failure by default. SMART, RAID, ZFS, UPS, and temperature checks require the relevant collector/exporter.
- A metric can be absent because the exporter, collector, permission, kernel feature, or filesystem type does not support it. Report this as a coverage gap, not as healthy.
- Avoid alerting on virtual filesystems, loop devices, container veth interfaces, and idle block devices unless they are the actual resource under review.
- Absence of pressure is only meaningful after scrape coverage, expected host inventory, time range, and retention are confirmed.
