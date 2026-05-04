---
name: homelab-loki-container-log-audit
description: >-
  Audits homelab container logs in Grafana Loki, especially Docker/container
  stdout and stderr streams such as {container!=""}. Covers security-relevant
  application and runtime events (authentication, authorization, admin actions,
  exposed services, secrets, SSRF/RCE/injection indicators, container exec or
  privilege signals) and application health issues (errors, crashes, panics,
  timeouts, database/cache failures, HTTP 5xx, rate limits, migrations, queues,
  TLS/DNS/network problems). Use when the user asks to review Loki container
  logs, audit application logs, scan Docker logs for security issues, or triage
  app failures across containers.
---

# Homelab Loki Container Log Audit

Use this skill when reviewing application and container stdout/stderr logs in Loki. This complements host journald review: host security events may live in `service_name="otel-collector"`, while this homelab's container application logs use the stream label `container` and usually mirror that value in `service_name`.

## Baseline selectors

Start by discovering the local labels instead of assuming one schema:

```logql
{container!=""} | limit 20
```

In this homelab, Grafana MCP has shown container logs with labels `container`, `host`, and `service_name`. The `job` label is used for host/file streams such as `dpkg` and `syslog`, not Docker container stdout/stderr. Do not start container audits with `{job="docker"}` unless live label discovery shows that stream exists.

If `{container!=""}` is empty, inspect Loki labels/datasource metadata or try likely selectors:

```logql
{container_name!=""} | limit 20
{compose_service!=""} | limit 20
{service!=""} | limit 20
```

Narrow the Grafana time range before expensive regex queries. In Markdown tables below, pipe characters are escaped as `\|`; use normal LogQL pipes when running queries.

## Review workflow

1. **Time range** - Set explicit start/end and note retention limits.
2. **Coverage check** - Identify active containers/services, last log time, missing expected services, and noisy streams.
3. **Schema pass** - Determine whether logs are plain text, JSON, logfmt, or mixed. Parse with `| json` or `| logfmt` when appropriate.
4. **Security pass** - Search authentication, authorization, admin, exploit, secret, and runtime abuse patterns. Capture service/container, timestamp, source IP/user, route/action, and evidence.
5. **Application pass** - Search crashes, errors, panics, failed dependencies, HTTP 5xx, queue/backlog, migration, TLS, DNS, timeout, and startup issues.
6. **Correlation pass** - Tie events together: external request -> auth failure/success -> admin action -> error spike -> container restart or dependency failure.
7. **Report** - Use the findings format below. Do not treat quiet searches as clean until coverage is confirmed.

### Using Grafana MCP (`user-grafana`)

- `list_datasources` with `type: loki` -> use returned `uid`.
- `query_loki_logs` with `datasourceUid`, `logql`, `startRfc3339`, `endRfc3339`, and `limit`.
- Avoid joining unrelated pipelines with `or`; use separate queries or a broad selector plus one concern-specific line filter.

## Coverage and metadata checks

| Concern | Example LogQL |
|--------|----------------|
| Confirm container streams have data | `{container!=""} \| limit 20` |
| Discover container names | `{container!=""} \| line_format "{{.container}}"` |
| JSON parse sample | `{container!=""} \| json \| limit 20` |
| logfmt parse sample | `{container!=""} \| logfmt \| limit 20` |
| Container starts/stops/restarts if present in logs | `{container!=""} \|~ "(?i)(starting|started|stopping|stopped|restart|restarting|shutdown|exiting)"` |
| Very noisy errors | `{container!=""} \|~ "(?i)(error|exception|panic|fatal|critical|traceback)"` |
| Missing or broken logging | `{container!=""} \|~ "(?i)(log.*(dropped|lost|truncated)|stdout.*closed|stderr.*closed|broken pipe)"` |

If `container` is not a label, inspect the returned labels and substitute the local service/container label in queries and reports.

## Security-focused LogQL

Tune these to the local applications. Run separate queries per concern and then inspect the surrounding timeline.

| Concern | Example LogQL |
|--------|----------------|
| Login failures | `{container!=""} \|~ "(?i)(login failed|failed login|authentication failed|invalid password|bad credentials|invalid token)"` |
| Login successes | `{container!=""} \|~ "(?i)(login successful|authenticated user|session created|token issued|oauth.*success)"` |
| Authorization failures | `{container!=""} \|~ "(?i)(forbidden|unauthorized|access denied|permission denied|not allowed|rbac|csrf)"` |
| Admin or sensitive actions | `{container!=""} \|~ "(?i)(admin|privilege|role changed|password changed|api key|token created|user created|user deleted|settings changed)"` |
| Brute force / rate limits | `{container!=""} \|~ "(?i)(rate limit|too many requests|brute force|throttl|blocked ip|ban)"` |
| Suspicious HTTP requests | `{container!=""} \|~ "(?i)(\\.env|/etc/passwd|wp-admin|phpmyadmin|cgi-bin|\\.git|id_rsa|config\\.php)"` |
| Injection / traversal indicators | `{container!=""} \|~ "(?i)(union select|select .* from|sleep\\(|benchmark\\(|\\.\\./|path traversal|template injection|xxe|deserializ)"` |
| RCE / shell indicators | `{container!=""} \|~ "(?i)(cmd=|exec=|/bin/sh|/bin/bash|powershell|curl .*\\|.*sh|wget .*\\|.*sh|reverse shell)"` |
| SSRF / metadata probing | `{container!=""} \|~ "(?i)(169\\.254\\.169\\.254|metadata\\.google|metadata\\.aws|instance-data|localhost:[0-9]+)"` |
| Secret leakage | `{container!=""} \|~ "(?i)(api[_-]?key|secret|password|passwd|token|authorization: bearer|private key|BEGIN .*PRIVATE KEY)"` |
| Container/runtime abuse in app logs | `{container!=""} \|~ "(?i)(docker exec|kubectl exec|privileged|mount /var/run/docker.sock|cap_add|host network|root user)"` |
| Webhook/auth callback failures | `{container!=""} \|~ "(?i)(webhook.*(invalid|failed|signature)|oauth.*(invalid|failed)|saml.*(invalid|failed))"` |

When reviewing security results, prefer structured fields such as `remote_addr`, `client_ip`, `user`, `username`, `method`, `path`, `status`, `request_id`, and `trace_id` if JSON/logfmt parsing exposes them.

## Application Issue LogQL

| Concern | Example LogQL |
|--------|----------------|
| Fatal errors / crashes | `{container!=""} \|~ "(?i)(fatal|panic|segmentation fault|core dumped|uncaught exception|traceback)"` |
| Generic errors | `{container!=""} \|~ "(?i)(error|exception|failed|failure)"` |
| HTTP 5xx | `{container!=""} \|~ "(?i)(\\s5[0-9]{2}\\s|status[=:]5[0-9]{2}|http.*5[0-9]{2})"` |
| Timeouts / cancellations | `{container!=""} \|~ "(?i)(timeout|timed out|context deadline exceeded|connection reset|connection refused|broken pipe)"` |
| Database failures | `{container!=""} \|~ "(?i)(postgres|mysql|mariadb|sqlite|database|db).*(error|failed|timeout|refused|deadlock|too many connections)"` |
| Redis/cache failures | `{container!=""} \|~ "(?i)(redis|cache|memcached).*(error|failed|timeout|refused|evicted)"` |
| Queue / worker issues | `{container!=""} \|~ "(?i)(queue|worker|job).*(failed|timeout|retry|dead letter|backlog|stuck)"` |
| Disk / storage in containers | `{container!=""} \|~ "(?i)(no space left|disk full|read-only file system|permission denied|i/o error)"` |
| TLS / certificate issues | `{container!=""} \|~ "(?i)(tls|ssl|certificate|x509).*(expired|invalid|verify failed|unknown authority)"` |
| DNS / upstream issues | `{container!=""} \|~ "(?i)(dns|lookup|resolve|upstream).*(failed|timeout|no such host|servfail)"` |
| Config / env problems | `{container!=""} \|~ "(?i)(missing env|missing config|invalid config|required.*not set|configuration error)"` |
| Migration / startup failures | `{container!=""} \|~ "(?i)(migration|migrate|startup|initiali[sz]e).*(failed|error|timeout)"` |
| Memory pressure in app logs | `{container!=""} \|~ "(?i)(out of memory|oom|memory limit|heap exhausted|cannot allocate memory)"` |

## Correlation checks

- Repeated auth failures followed by a successful login from the same IP, username, or user agent.
- New admin/API token/user creation near suspicious request patterns.
- Secret leakage followed by authentication or webhook failures.
- 5xx/error spike after deployment, restart, migration, configuration change, or dependency outage.
- Timeouts across multiple services pointing to one upstream database, cache, DNS, proxy, or storage service.
- Application errors followed by container restart logs or host-level OOM/systemd events.
- Same source IP hitting multiple applications or routes.

## Findings format

Produce a short report:

```markdown
## Loki container log audit (<time range>)

### Summary
- Streams reviewed: ...
- Services/containers seen: ...
- Expected services missing: ...
- Time range / gaps: ...

### Security findings
- **<Severity> - <finding title>**
  - Service / container: ...
  - Time: ...
  - Evidence: One-line excerpt / parsed fields.
  - Suggested action: ...

### Application findings
- **<Severity> - <finding title>**
  - Service / container: ...
  - Time: ...
  - Evidence: One-line excerpt / parsed fields.
  - Suggested action: ...

### Correlations
- Timeline-style notes connecting requests, auth, admin actions, errors, restarts, and dependency failures.

### False positives / noise
- Patterns tuned out: ...

### Follow-ups
- Queries to schedule / alerts to add: ...
```

**Severity guidance:** Critical (confirmed exploit, exposed secrets with evidence of use, unauthorized admin action, destructive action, or active RCE). High (successful suspicious login, new admin/API token from unknown source, repeated 5xx affecting core apps, dependency outage with user impact). Medium (targeted auth failures, suspicious probes against sensitive routes, recurring exceptions, queue backlog, certificate/DNS/database errors without confirmed outage). Low (background scans, isolated expected errors, known maintenance noise).

Raise severity for privileged users, unknown source IPs, unusual times, multiple services, success after failures, secret exposure, persistence/admin changes, and correlated host-level events. Lower severity for expected automation, health checks, known scanners, and maintenance windows.

## Important caveats

- Container log labels vary by collector: confirm the local label schema before relying on examples.
- Application logs may be JSON, logfmt, or plain text; parse when possible and report structured fields.
- Avoid dumping secrets in the final report. Mention that a secret-like value appeared, include its field/source, and redact the value.
- Loki regex support and extracted-field filtering differ by version and pipeline. If a query errors, simplify it and search message text first.
- Absence of evidence is only useful after coverage, time range, expected services, retention, and logging health are checked.
