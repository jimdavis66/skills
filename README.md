# Skills

This repository contains personal AI agent skills: small, self-contained
instruction packages that teach an assistant how to perform a specific workflow
with the right context, commands, output shape, and guardrails.

Each skill lives under `skills/` in its own directory and is centered on a
`SKILL.md` file. Some skills also include helper scripts, README files, agent
metadata, or local development notes.

## Repository Contents

| Skill | Purpose |
| --- | --- |
| [`homelab-container-metrics-audit`](skills/homelab-container-metrics-audit/) | Audit homelab container resource health using Grafana Prometheus cAdvisor metrics. Includes cAdvisor coverage, CPU, memory/OOM, filesystem/inode, I/O, network, process/thread/file descriptor, PSI pressure checks, thresholds, and intervention-focused reporting. |
| [`homelab-host-metrics-audit`](skills/homelab-host-metrics-audit/) | Audit homelab host resource health using Grafana Prometheus metrics. Includes discovery, coverage checks, CPU/load, memory/swap, filesystem/inode, disk I/O, network, reboot, hardware/storage-health checks, thresholds, and intervention-focused reporting. |
| [`homelab-loki-container-log-audit`](skills/homelab-loki-container-log-audit/) | Audit homelab container logs in Grafana Loki. Includes LogQL patterns for security-related application events, suspicious requests, secrets, runtime abuse signals, application errors, dependency failures, and findings reports. |
| [`homelab-loki-host-log-audit`](skills/homelab-loki-host-log-audit/) | Review homelab host logs shipped through OpenTelemetry Collector to Grafana Loki. Includes LogQL patterns for host coverage, security review, operational issues, correlation, and findings reports. |
| [`nzbgeek-classical-lossless`](skills/nzbgeek-classical-lossless/) | Scan NZBGeek `Audio > Lossless` category `3040` for likely classical releases from the last 24 hours. Includes Python scripts for filtering results, optional OpenAI classification, Discogs matching, and optional SABnzbd delivery. |
| [`swsd-comment-style`](skills/swsd-comment-style/) | Draft or post SolarWinds Service Desk incident comments in a practical school ICT support tone. Includes ticket context gathering, public vs private notes, voice and style rules, and draft-before-post guardrails. |

## Using a Skill

Install or expose the relevant directory under `skills/` to an agent runtime
that supports skills, then ask for the workflow described by that skill. For example:

- Ask for a homelab Loki host log audit to trigger `homelab-loki-host-log-audit`.
- Ask for a homelab Loki container log audit to trigger `homelab-loki-container-log-audit`.
- Ask for a homelab host metrics audit to trigger `homelab-host-metrics-audit`.
- Ask for a homelab container metrics audit to trigger `homelab-container-metrics-audit`.
- Ask for a current NZBGeek classical lossless scan to trigger `nzbgeek-classical-lossless`.
- Ask to draft or post an SWSD incident comment to trigger `swsd-comment-style`.

## Adding a Skill

Create a new directory under `skills/` with at least:

```text
skills/new-skill-name/
└── SKILL.md
```

Keep the skill focused on one workflow. A useful `SKILL.md` should explain:

- When the skill applies.
- What commands or tools to run.
- Required and optional environment variables.
- Expected output format.
- Known caveats, failure modes, or safety constraints.

If the skill needs implementation code, place it under a local `scripts/`
directory and document the entry points in the skill README.
