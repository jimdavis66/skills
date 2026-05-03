# Skills

This repository contains personal AI agent skills: small, self-contained
instruction packages that teach an assistant how to perform a specific workflow
with the right context, commands, output shape, and guardrails.

Each skill lives in its own directory and is centered on a `SKILL.md` file. Some
skills also include helper scripts, README files, agent metadata, or local
development notes.

## Repository Contents

| Skill | Purpose |
| --- | --- |
| [`homelab-otel-loki-review`](homelab-otel-loki-review/) | Review homelab host logs shipped through OpenTelemetry Collector to Grafana Loki. Includes LogQL patterns for host coverage, security review, operational issues, correlation, and findings reports. |
| [`nzbgeek-classical-lossless`](nzbgeek-classical-lossless/) | Scan NZBGeek `Audio > Lossless` category `3040` for likely classical releases from the last 24 hours. Includes Python scripts for filtering results, optional OpenAI classification, Discogs matching, and optional SABnzbd delivery. |

## Using a Skill

Install or expose the relevant skill directory to an agent runtime that supports
skills, then ask for the workflow described by that skill. For example:

- Ask for a homelab Loki log review to trigger `homelab-otel-loki-review`.
- Ask for a current NZBGeek classical lossless scan to trigger `nzbgeek-classical-lossless`.

## Adding a Skill

Create a new directory with at least:

```text
new-skill-name/
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
