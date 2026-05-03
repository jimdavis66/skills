---
name: homelab-loki-host-log-audit
description: >-
  Reviews homelab host logs shipped by OpenTelemetry Collector to Grafana Loki
  using LogQL on {service_name="otel-collector"}. Covers security-relevant
  patterns (SSH, PAM, sudo, account changes, persistence, logging tamper
  signals) and operational signals (kernel, systemd, disk, OOM, boot, time,
  network, storage). Use when the user asks to audit OTel/Loki logs, scan
  hosts for security issues, triage journald across all hosts, or apply a
  structured log review workflow.
---

# Homelab Loki Host Log Audit

Host logs from this repository’s OpenTelemetry stack land in Loki with the OTLP-derived label **`service_name="otel-collector"`**. Journal fields (e.g. `_HOSTNAME`, `MESSAGE`, `_SYSTEMD_UNIT`, `PRIORITY`) usually appear in the **log line** (often JSON) or structured metadata, not always as stream labels.

## Baseline selector

Always anchor on the OTel collector stream:

```logql
{service_name="otel-collector"}
```

Narrow time range in Grafana (e.g. last 1–24h) before expensive queries.

In Markdown tables below, pipe characters are escaped as `\|` so rows render correctly. When running a query in Grafana or Grafana MCP, use normal LogQL pipe characters.

## Identifying which host

- **Parse JSON body** when the line is journal JSON, then read **`_HOSTNAME`** and **`MESSAGE`** in Grafana Explore (table) or add `| line_format` once field names match your Loki JSON parser output:

```logql
{service_name="otel-collector"} | json
```

- **`_HOSTNAME`** inside the journal payload is the **systemd-reported hostname** for that log event (often aligns with the real host).
- Useful journald fields to inspect after `| json`: `_HOSTNAME`, `MESSAGE`, `_SYSTEMD_UNIT`, `SYSLOG_IDENTIFIER`, `PRIORITY`, `_TRANSPORT`, `_PID`, `_UID`, `_GID`, `_EXE`, `_CMDLINE`, `_BOOT_ID`.

## Review workflow

1. **Time range** — Set explicit start/end; remember collectors use **`start_at: end`** on journald/filelog, so history only exists from last collector start unless configs change.
2. **Coverage check** — Confirm which hosts are reporting, the last log time per host, and whether any expected host is silent.
3. **Volume check** — Run a cheap query first (short window or `| limit 20`) to avoid scanning huge ranges; then look for sudden drops or spikes.
4. **Metadata pass** — Parse JSON and inspect journald fields, especially `_HOSTNAME`, `_SYSTEMD_UNIT`, `SYSLOG_IDENTIFIER`, `PRIORITY`, `_BOOT_ID`, `_EXE`, and `_CMDLINE`.
5. **Security pass** — Run the patterns in [Security-focused LogQL](#security-focused-logql); note host, timestamp, `MESSAGE`, unit, source IP/user, and executable if present.
6. **Correlation pass** — Connect related events into timelines: login → sudo/su → account change → package install → service/timer creation → logging gap.
7. **Ops pass** — Run [Operational signals](#operational-signals) for crashes, OOM, disk, failed units, boot/time/network/storage issues.
8. **Report** — Use [Findings format](#findings-format).

### Using Grafana MCP (`user-grafana`)

- `list_datasources` with `type: loki` → use returned **`uid`** (often `loki`).
- `query_loki_logs` with `datasourceUid`, `logql`, `startRfc3339`, `endRfc3339`, `limit` (default cap often 100—increase only if needed).
- **Do not** combine unrelated pipelines with `or`; use separate queries or a single selector that matches all needed streams, then line filters.

## Coverage and metadata checks

Do these before judging security or ops health. "No findings" is not meaningful until expected hosts are known to be reporting.

| Concern | Example LogQL |
|--------|----------------|
| Confirm log stream has data | `{service_name="otel-collector"} \| limit 20` |
| Discover hosts in range | `{service_name="otel-collector"} \| json \| line_format "{{._HOSTNAME}}"` |
| Collector or shipping errors | `{service_name="otel-collector"} \|~ "(?i)(otelcol\|otel-collector\|exporter\|receiver\|loki).*?(error\|failed\|refused\|timeout\|unauthorized\|tls)"` |
| Journal/logging gaps | `{service_name="otel-collector"} \|~ "(?i)(systemd-journald.*(stopped\|started\|rotat\|vacuum)\|journal.*(corrupt\|missed\|dropped)\|otel-collector.*(stopped\|started\|restarted))"` |
| Emergency through error priority | `{service_name="otel-collector"} \| json \| PRIORITY=~"[0-3]"` |
| Boot/session boundary | `{service_name="otel-collector"} \| json \|~ "(?i)(Linux version\|Startup finished\|Shutting down\|Reached target)"` |

If extracted field filters do not work in the local Loki version, keep `| json`, use Explore table view, and fall back to `|~` message filters.

## Security-focused LogQL

Run separately or combine line filters after one selector. Adjust for noise in your environment.

| Concern | Example LogQL |
|--------|----------------|
| SSH successful key/password auth | `{service_name="otel-collector"} \|~ "(?i)accepted (publickey\|password\|keyboard-interactive) for"` |
| SSH failures / probes | `{service_name="otel-collector"} \|~ "(?i)(failed password\|invalid user\|connection (closed\|reset)\|bad ownership\|maximum authentication attempts)"` |
| SSH source/user correlation | `{service_name="otel-collector"} \|~ "(?i)(accepted .* for .* from\|failed password for .* from\|invalid user .* from)"` |
| SSH key or permission issues | `{service_name="otel-collector"} \|~ "(?i)(authorized_keys\|bad ownership\|bad modes\|Authentication refused\|host key.*changed\|REMOTE HOST IDENTIFICATION HAS CHANGED)"` |
| sudo command execution | `{service_name="otel-collector"} \|~ "(?i)sudo: .*COMMAND="` |
| sudo failures / policy violations | `{service_name="otel-collector"} \|~ "(?i)(sudo: .*incorrect password\|sudo: .*not in the sudoers\|sudo: .*authentication failure\|pam_unix\\(sudo:auth\\))"` |
| su / pkexec / polkit / doas | `{service_name="otel-collector"} \|~ "(?i)(su:.*(session opened\|authentication failure)\|pkexec\|polkit.*(auth\|denied\|granted)\|doas:)"` |
| PAM auth failures | `{service_name="otel-collector"} \|~ "(?i)pam_unix.*authentication failure"` |
| User / session churn | `{service_name="otel-collector"} \|~ "(?i)(session opened\|session closed) for user"` |
| Account and group changes | `{service_name="otel-collector"} \|~ "(?i)(useradd\|usermod\|userdel\|groupadd\|groupmod\|groupdel\|passwd\|chage\|gpasswd).*"` |
| Service persistence | `{service_name="otel-collector"} \|~ "(?i)(Created symlink .*\\.service\|Created symlink .*\\.timer\|systemctl.*(enable\|preset)\|Reloading.*systemd\|daemon-reload)"` |
| Timer/socket persistence | `{service_name="otel-collector"} \|~ "(?i)(\\.timer\|\\.socket).*(enabled\|started\|created symlink)"` |
| Cron/anacron activity | `{service_name="otel-collector"} \|~ "(?i)(CRON\\[\|cron\\[\|anacron\|crontab)"` |
| Package changes near suspicious activity | `{service_name="otel-collector"} \|~ "(?i)(dpkg:.*(install\|upgrade\|remove)\|apt.*(install\|remove\|upgrade)\|dnf.*(install\|remove)\|yum.*(install\|remove))"` |
| Firewall changes / denied traffic | `{service_name="otel-collector"} \|~ "(?i)(nft\|iptables\|ufw\|firewalld).*(allow\|deny\|drop\|reject\|reload\|rule)"` |
| Audit/AppArmor/SELinux/seccomp denials | `{service_name="otel-collector"} \|~ "(?i)(audit:.*(denied\|avc\|apparmor\|seccomp)\|apparmor=.*DENIED\|SELinux.*denied\|avc:.*denied)"` |
| Kernel module / BPF / ptrace signals | `{service_name="otel-collector"} \|~ "(?i)(module verification failed\|loading out-of-tree module\|kernel is tainted\|lockdown\|BPF\|ptrace\|kprobe)"` |
| Container runtime security events | `{service_name="otel-collector"} \|~ "(?i)(docker\|containerd\|runc\|podman).*(start\|exec\|privileged\|mount\|capability\|apparmor\|seccomp)"` |
| Logging or collector tampering | `{service_name="otel-collector"} \|~ "(?i)(systemd-journald\|auditd\|rsyslog\|otel-collector).*(stopped\|disabled\|failed\|killed)"` |

After `| json`, you can filter on extracted keys if Loki version supports it, e.g. filters on `MESSAGE` or `_SYSTEMD_UNIT` depending on parser.

When reviewing sudo, capture the invoking user, target user, TTY, PWD, and `COMMAND=`. A single privileged command can be more important than a large number of low-quality SSH probes.

## Correlation checks

Use these to turn isolated messages into security stories:

- SSH failure burst from one source IP, followed by an accepted login.
- Accepted login for a privileged or rarely used account, followed by `sudo`, `su`, `pkexec`, or `polkit`.
- Privileged session followed by account/group changes.
- Privileged session followed by package install, service enablement, timer creation, cron edit, or firewall change.
- Any sensitive action followed by journald, auditd, rsyslog, or collector restart/stop.
- Internal host login after external-facing host login, which may indicate lateral movement.
- Same source IP touching multiple hosts or multiple valid usernames.

## Operational signals

| Concern | Example LogQL |
|--------|----------------|
| systemd unit failures | `{service_name="otel-collector"} \|~ "(?i)(failed with result\|\.service: (Main process exited\|Failed with result))"` |
| systemd restart loops | `{service_name="otel-collector"} \|~ "(?i)(Start request repeated too quickly\|Scheduled restart job\|restart counter\|Failed to start)"` |
| OOM / memory | `{service_name="otel-collector"} \|~ "(?i)(out of memory\|oom-kill\|Kill process)"` |
| Disk / filesystem | `{service_name="otel-collector"} \|~ "(?i)(no space left on device\|I/O error\|read-only file system\|EXT4-fs error\|XFS.*(error\|corruption)\|BTRFS.*(error\|corrupt))"` |
| Storage hardware / block layer | `{service_name="otel-collector"} \|~ "(?i)(SMART\|nvme.*(error\|reset\|timeout)\|blk_update_request\|Buffer I/O error\|medium error\|md/raid\|zfs.*(error\|faulted\|degraded))"` |
| segfault / core | `{service_name="otel-collector"} \|~ "(?i)(segfault at\|core dumped)"` |
| kernel panic / lockup / hung task | `{service_name="otel-collector"} \|~ "(?i)(kernel panic\|Oops:\|hung task\|blocked for more than\|soft lockup\|hard LOCKUP\|RCU stall\|watchdog)"` |
| reboot / shutdown / boot | `{service_name="otel-collector"} \|~ "(?i)(Linux version\|Startup finished\|Shutting down\|Reached target (Shutdown\|Reboot)\|systemd-shutdown)"` |
| time sync / clock jumps | `{service_name="otel-collector"} \|~ "(?i)(systemd-timesyncd\|chronyd\|ntpd\|NTP\|Time has been changed\|Clock jumped\|time sync)"` |
| network link / DHCP / DNS | `{service_name="otel-collector"} \|~ "(?i)(Link is Down\|Link is Up\|carrier lost\|DHCP.*(failed\|timeout\|lease)\|NetworkManager\|systemd-networkd\|DNS.*(failed\|timeout))"` |
| thermal / machine check | `{service_name="otel-collector"} \|~ "(?i)(thermal.*(throttl\|critical)\|temperature above threshold\|mce:\|Machine Check\|hardware error)"` |
| dpkg / updates (file_log) | `{service_name="otel-collector"} \|~ "(?i)dpkg:.*(install\|upgrade\|remove)"` (tune; file tail body may differ) |

## Findings format

Produce a short report:

```markdown
## OTel / Loki log review (<time range>)

### Summary
- Streams reviewed: `{service_name="otel-collector"}`
- Hosts seen: …
- Expected hosts missing: …
- Time range / gaps: …

### Security findings
| Severity | Host | Time | Evidence | Suggested action |
|----------|------|------|----------|------------------|
| … | … | … | One-line excerpt / unit | … |

### Operational findings
(same table or bullets)

### Correlations
- Timeline-style notes for related login, privilege, persistence, package, service, and logging events.

### False positives / noise
- Patterns tuned out: …

### Follow-ups
- Queries to schedule / alerts to add: …
```

**Severity guidance:** Critical (confirmed compromise, destructive action, active persistence, credential theft indicators, or lateral movement). High (successful privileged login from unknown source, success after brute force, suspicious sudo/su/pkexec, new privileged account, logging disabled, unauthorized service/timer). Medium (targeted auth failures, scans against valid users, single failed service with user impact, storage/kernel errors without confirmed outage). Low (background internet probes, expected package updates, informational session churn).

Raise severity when the event involves privileged accounts, new source IPs, unusual times, multiple hosts, success after failures, persistence creation, firewall/logging changes, or missing logs. Lower severity for known maintenance windows, expected automation, and noisy external scans with no valid user or success.

## Important caveats

- **Not all hosts** may ship on the same stream if some use Promtail only; Docker container stdout on full Docker hosts is often **`{job="docker"}`**—this skill is **OTel host logs** only.
- **Cardinality** — Avoid turning high-cardinality journal keys into Loki labels; filter in LogQL or Explore fields instead.
- **TLS / egress** — If a host stops shipping, check collector container logs and network to the Loki OTLP URL, not only Loki queries.
- **Regex portability** — Loki regex support and extracted-field filtering differ by version and pipeline. If a query errors, simplify it, keep the same concern, and search message text first.
- **Absence of evidence** — A quiet query is only useful after host coverage, collector health, time range, and retention have been checked.
