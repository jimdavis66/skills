---
name: homelab-container-metrics-audit
description: >-
  Audits homelab container resource health using Grafana Prometheus metrics
  from cAdvisor. Covers cAdvisor scrape coverage, active container discovery,
  CPU usage and throttling, memory working set and limits, OOM events, restart
  age, filesystem usage and inode pressure, container I/O, network errors and
  drops, process/thread/file descriptor pressure, PSI pressure metrics when
  exported, and human intervention thresholds. Use when the user asks to check
  Docker/container metrics, cAdvisor health, container resource pressure,
  capacity risk, or whether any container needs intervention.
---

# Homelab Container Metrics Audit

Use this skill to answer: "Are any containers under resource pressure and do they need human intervention?" Prefer cAdvisor metrics for resource pressure, then correlate with Loki container logs for root cause and impact.

In this homelab, cAdvisor uses `job="cAdvisor"` across Docker hosts, and each host has its own `instance` label. Docker container names are in the `name` label. Always preserve both `instance` and `name` in aggregations and reports so same-named containers on different hosts, such as `traefik` on `docker-prod-1` and `docker-prod-2`, are audited separately.

## Baseline workflow

1. **Time range** - Use last 1h for current pressure and last 24h or 7d for trends, OOMs, restarts, and capacity changes.
2. **Datasource discovery** - In Grafana MCP, run `list_datasources` with `type: prometheus` and use the returned `uid`.
3. **Metric discovery** - Confirm cAdvisor exists:
   - `list_prometheus_metric_names` with regex `^container_.*`
   - `list_prometheus_label_values` for `job`, then find the cAdvisor job, usually `cAdvisor` in this homelab.
   - `list_prometheus_label_values` for `name`, `container`, `container_label_com_docker_compose_service`, `image`, and `instance` scoped to the cAdvisor job.
4. **Coverage check** - Identify cAdvisor hosts from `instance`, active containers per host, missing expected services, scrape failures, and stale series.
5. **Pressure pass** - Run CPU, memory, OOM, filesystem, I/O, network, process/thread, and PSI checks.
6. **Trend pass** - For capacity and leak-like behavior, compare current values to 1h/24h maxima and trends.
7. **Triage** - Assign severity using the guidance below and recommend concrete actions.
8. **Report** - Use the findings format at the end.

## Using Grafana MCP

- `list_datasources` with `type: prometheus` -> use returned `uid`.
- `list_prometheus_metric_names` -> discover available `container_*` metrics.
- `list_prometheus_label_values` -> discover `job`, `instance`, `name`, `container`, `image`, and Docker/Compose label values.
- `query_prometheus` -> run instant or range PromQL with `datasourceUid`, `expr`, `queryType`, `startTime`, `endTime`, and `stepSeconds`.

Start with instant queries for current pressure, then use range queries for restarts, OOMs, and sustained resource pressure.

## Baseline selectors

Use the local cAdvisor selector after discovery. In this homelab, start with:

```promql
{job="cAdvisor", name!=""}
```

Treat `instance` as the host dimension. For a specific container on one host:

```promql
{job="cAdvisor", instance="docker-prod-1:8082", name="traefik"}
```

Adjust the `instance` value to whatever discovery returns; do not assume the port.

In metric queries, exclude infrastructure, pause, and root cgroup series when needed:

```promql
job="cAdvisor", name!="", image!="", name!~"^/$|POD"
```

If `name` is missing, try `container`, `container_name`, `container_label_com_docker_compose_service`, or `id`. Prefer the most human-readable stable label in reports.

When aggregating, prefer `by (instance, name)` rather than `by (name)`. Aggregating only by `name` merges same-named containers across hosts and can hide host-specific pressure.

## Coverage and scrape health

Run these before judging container health.

| Concern | Example PromQL |
|--------|----------------|
| cAdvisor scrape target down | `up{job=~"(?i)cadvisor"} == 0` |
| cAdvisor scrape errors | `container_scrape_error{job=~"(?i)cadvisor"} != 0` |
| cAdvisor hosts seen | `count by (instance) (up{job="cAdvisor"})` |
| Active containers seen by host | `count by (instance, name) (container_last_seen{job="cAdvisor", name!=""})` |
| Specific service on each host | `container_last_seen{job="cAdvisor", name="traefik"}` |
| Recently stale containers | `time() - container_last_seen{job=~"(?i)cadvisor", name!=""} > 300` |
| Container start age | `time() - container_start_time_seconds{job=~"(?i)cadvisor", name!=""}` |
| Containers restarted in 24h | `changes(container_start_time_seconds{job=~"(?i)cadvisor", name!=""}[24h]) > 0` |

If `job=~"(?i)cadvisor"` returns no data, use `job="cAdvisor"` first, then discover the exact job value and substitute it.

## CPU pressure

| Concern | Example PromQL | Human threshold |
|--------|----------------|-----------------|
| CPU cores used | `sum by (instance, name) (rate(container_cpu_usage_seconds_total{job="cAdvisor", name!="", image!=""}[5m]))` | Interpret relative to expected workload and host capacity |
| CPU percentage of one core | `100 * sum by (instance, name) (rate(container_cpu_usage_seconds_total{job="cAdvisor", name!="", image!=""}[5m]))` | Sustained > 100% means more than one core; only a problem if unexpected |
| CPU for one service across hosts | `100 * sum by (instance, name) (rate(container_cpu_usage_seconds_total{job="cAdvisor", name="traefik", image!=""}[5m]))` | Use to compare the same service on different hosts |
| CPU share weighting if useful | `container_spec_cpu_shares{job="cAdvisor", name!="", image!=""}` | Use only as context; shares are not a hard CPU limit |
| CPU load average | `container_cpu_load_average_10s{job="cAdvisor", name!="", image!=""}` | High only when paired with throttling or latency |
| CPU pressure waiting | `rate(container_pressure_cpu_waiting_seconds_total{job="cAdvisor", name!="", image!=""}[5m])` | Sustained non-zero with latency is Medium/High |
| CPU pressure stalled | `rate(container_pressure_cpu_stalled_seconds_total{job="cAdvisor", name!="", image!=""}[5m])` | Sustained non-zero is stronger evidence of pressure |

cAdvisor CPU quota metrics are often absent. If `container_spec_cpu_quota` and `container_spec_cpu_period` exist locally, use them to calculate quota utilization; otherwise report CPU usage in cores and correlate with host CPU/load from `homelab-host-metrics-audit`.

## Memory pressure and OOMs

Prefer `container_memory_working_set_bytes` for practical memory pressure. Compare it to `container_spec_memory_limit_bytes` only when the limit is sane and non-zero.

| Concern | Example PromQL | Human threshold |
|--------|----------------|-----------------|
| Working set bytes | `container_memory_working_set_bytes{job="cAdvisor", name!="", image!=""}` | Rank top consumers and compare to expected service size |
| Memory usage vs limit | `100 * container_memory_working_set_bytes{job="cAdvisor", name!="", image!=""} / container_spec_memory_limit_bytes{job="cAdvisor", name!="", image!=""}` | > 80% Medium; > 90% High; > 95% Critical when the limit is real |
| Memory for one service across hosts | `container_memory_working_set_bytes{job="cAdvisor", name="traefik", image!=""}` | Compare same-named containers by `instance` |
| Memory fail count increase | `increase(container_memory_failcnt{job="cAdvisor", name!="", image!=""}[1h])` | Any sustained increase is Medium/High |
| Memory failures by type | `increase(container_memory_failures_total{job="cAdvisor", name!="", image!=""}[1h])` | Failures near limit need review |
| OOM events | `increase(container_oom_events_total{job="cAdvisor", name!="", image!=""}[24h])` | Any OOM is High; repeated OOMs are Critical |
| Memory pressure waiting | `rate(container_pressure_memory_waiting_seconds_total{job="cAdvisor", name!="", image!=""}[5m])` | Sustained non-zero with high working set is High |
| Memory pressure stalled | `rate(container_pressure_memory_stalled_seconds_total{job="cAdvisor", name!="", image!=""}[5m])` | Sustained non-zero is High |

Some cAdvisor setups expose very large memory limits for unlimited containers. Treat enormous limits as no useful limit; report absolute memory and correlate with host memory instead.

## Filesystem and inode pressure

Container filesystem metrics may represent writable layers, bind mounts, or volume-backed paths depending on runtime and cAdvisor config.

| Concern | Example PromQL | Human threshold |
|--------|----------------|-----------------|
| Filesystem used percentage | `100 * container_fs_usage_bytes{job="cAdvisor", name!="", image!=""} / container_fs_limit_bytes{job="cAdvisor", name!="", image!=""}` | > 80% Medium; > 90% High; > 95% Critical |
| Filesystem bytes used | `container_fs_usage_bytes{job="cAdvisor", name!="", image!=""}` | Rank top consumers |
| Inode used percentage | `100 * (1 - container_fs_inodes_free{job="cAdvisor", name!="", image!=""} / container_fs_inodes_total{job="cAdvisor", name!="", image!=""})` | > 85% Medium; > 90% High; > 95% Critical |
| Filesystem I/O current | `container_fs_io_current{job="cAdvisor", name!="", image!=""}` | Sustained non-zero can indicate blocked I/O |
| Write bytes rate | `rate(container_fs_writes_bytes_total{job="cAdvisor", name!="", image!=""}[5m])` | Useful for finding growth source |
| Read/write latency approximation | `rate(container_fs_write_seconds_total{job="cAdvisor", name!="", image!=""}[5m]) / rate(container_fs_writes_total{job="cAdvisor", name!="", image!=""}[5m])` | > 50ms review; > 200ms High |

If container filesystem pressure appears, correlate with host filesystem pressure and identify whether the affected path is a Docker writable layer, named volume, bind mount, NFS/CIFS mount, database data directory, media/download directory, or logs.

## Network pressure and errors

| Concern | Example PromQL | Human threshold |
|--------|----------------|-----------------|
| Receive error rate | `rate(container_network_receive_errors_total{job="cAdvisor", name!="", image!=""}[5m])` | Sustained non-zero is Medium/High |
| Transmit error rate | `rate(container_network_transmit_errors_total{job="cAdvisor", name!="", image!=""}[5m])` | Sustained non-zero is Medium/High |
| Receive drops | `rate(container_network_receive_packets_dropped_total{job="cAdvisor", name!="", image!=""}[5m])` | Sustained drops need review |
| Transmit drops | `rate(container_network_transmit_packets_dropped_total{job="cAdvisor", name!="", image!=""}[5m])` | Sustained drops need review |
| Network throughput | `rate(container_network_receive_bytes_total{job="cAdvisor", name!="", image!=""}[5m]) + rate(container_network_transmit_bytes_total{job="cAdvisor", name!="", image!=""}[5m])` | Rank top talkers; high alone is not pressure |
| TCP sockets if exported | `container_network_tcp_usage_total{job="cAdvisor", name!="", image!=""}` | Watch for abnormal growth |

Do not treat high throughput alone as a problem unless it approaches host/link capacity or correlates with packet drops, errors, service latency, or upstream failures.

## Process, thread, and file descriptor pressure

| Concern | Example PromQL | Human threshold |
|--------|----------------|-----------------|
| Processes | `container_processes{job="cAdvisor", name!="", image!=""}` | Sudden growth may indicate leaks or fork storms |
| Threads | `container_threads{job="cAdvisor", name!="", image!=""}` | Sudden growth or near max is Medium/High |
| Threads vs max | `100 * container_threads{job="cAdvisor", name!="", image!=""} / container_threads_max{job="cAdvisor", name!="", image!=""}` | > 80% Medium; > 90% High |
| File descriptors | `container_file_descriptors{job="cAdvisor", name!="", image!=""}` | Rank and trend; correlate with app errors |
| Soft ulimits | `container_ulimits_soft{job="cAdvisor", name!="", image!=""}` | Compare if label exposes `ulimit` or resource type |

Use trend checks for leaks: `max_over_time(metric[24h])` and `changes`/slope are more useful than one snapshot.

## Correlation checks

- Container OOM event followed by restart and Loki errors.
- High memory usage near limit + memory failures + app latency or restart.
- CPU pressure + high host CPU/load from `homelab-host-metrics-audit`.
- Container filesystem growth + host mount over capacity threshold.
- High write rate from one container + host disk I/O or iowait pressure.
- Network drops/errors in cAdvisor + host NIC drops/errors + application timeouts.
- Restarts after deployments or maintenance windows versus unplanned restart loops.
- Multiple containers on one host degraded by the same storage, network, DNS, or database dependency.

## Findings format

Produce a short report:

```markdown
## Grafana Prometheus container metrics audit (<time range>)

### Summary
- Datasource: ...
- cAdvisor selector: ...
- Containers reporting: ...
- Expected containers missing: ...
- Overall status: Healthy / Watch / Intervention needed

### Intervention findings
- **<Severity> - <finding title>**
  - Container: ...
  - Host / instance: ...
  - Metric(s): ...
  - Current / peak: ...
  - Time window: ...
  - Why it matters: ...
  - Suggested action: ...

### Watchlist
- Containers close to threshold, trending badly, or showing low-grade drops/failures.

### Coverage gaps
- Missing labels, absent limits, stale containers, absent PSI/network/filesystem metrics, or unknown expected inventory.

### Follow-ups
- Logs to correlate, alerts to add, compose/service limits to tune, or host checks to run.
```

**Severity guidance:** Critical (repeated OOMs or restart loop causing outage, filesystem/inode >95%, container cannot write, severe memory/CPU pressure with user impact, container down unexpectedly). High (any OOM, memory >90% of real limit, sustained CPU quota saturation, sustained PSI stalls, filesystem >90%, high network errors/drops with service impact, thread/process exhaustion). Medium (memory >80% of real limit, rising fail counts, filesystem >80%, unexpected restart, sustained moderate packet drops, abnormal growth trend). Low (short spikes, expected restarts, high throughput without errors, idle stopped containers, metrics noise from infrastructure containers).

Raise severity when the container is user-facing, stateful, security-critical, or a shared dependency such as database, cache, DNS, reverse proxy, auth, monitoring, MQTT, or home automation. Lower severity for planned jobs, backups, batch workloads, known deployments, and containers without real limits where host metrics are healthy.

## Important caveats

- cAdvisor label schemas vary. Discover labels and choose the human-readable container/service label before running fixed queries.
- Many containers do not have CPU or memory limits. Limit-percentage queries are only meaningful when limits are real and finite.
- cAdvisor filesystem metrics can be confusing with bind mounts and network mounts. Correlate with host filesystem metrics before deciding the intervention target.
- OOM counters and restart signals depend on runtime/cAdvisor support. If missing, correlate with container logs and Docker/Compose state.
- A quiet query is only useful after cAdvisor scrape health, expected container inventory, time range, and retention are confirmed.
