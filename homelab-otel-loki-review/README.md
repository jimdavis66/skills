# homelab-otel-loki-review

An AI skill for reviewing homelab host logs shipped through OpenTelemetry Collector to Grafana Loki.

The skill focuses on the Loki stream:

```logql
{service_name="otel-collector"}
```

It provides a structured workflow for checking host coverage, reviewing security-relevant events, finding operational problems, and writing concise findings from Loki or Grafana MCP queries.

## What It Covers

- SSH authentication successes, failures, and probe activity
- sudo, su, PAM, polkit, and privilege escalation events
- Account, group, package, service, timer, cron, and firewall changes
- Logging gaps, collector failures, and tamper signals
- systemd failures, OOM events, disk errors, kernel issues, boot events, time sync, network, and storage problems

## Usage

Install or enable this directory in an AI assistant that supports skill-style instructions, then ask it to review OTel/Loki host logs, audit homelab logs, scan hosts for security issues, or triage journald events across hosts.

The full skill instructions and LogQL query library are in [`SKILL.md`](SKILL.md).

## Notes

- Start with a narrow Grafana time range before running expensive queries.
- Confirm expected hosts are reporting before treating quiet searches as clean results.
- Journal fields such as `_HOSTNAME`, `MESSAGE`, `_SYSTEMD_UNIT`, and `PRIORITY` usually need JSON parsing or table inspection rather than label filtering.
