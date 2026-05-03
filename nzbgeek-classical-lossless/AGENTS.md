# Repository Guidelines

## Project Structure & Module Organization

This repository is a compact Codex skill package. [`SKILL.md`](/Users/james_davis/repositories/skills/nzbgeek-classical-lossless/SKILL.md) defines the skill contract and expected output behavior. [`scripts/check_nzbgeek_classical_lossless.py`](/Users/james_davis/repositories/skills/nzbgeek-classical-lossless/scripts/check_nzbgeek_classical_lossless.py) contains the full implementation: NZBGeek queries, heuristic filtering, optional OpenAI review, and Discogs matching. [`agents/openai.yaml`](/Users/james_davis/repositories/skills/nzbgeek-classical-lossless/agents/openai.yaml) provides the agent-facing metadata. Treat `scripts/__pycache__/` as generated output, not source.

## Build, Test, and Development Commands

There is no separate build step. Use Python 3 directly:

```bash
python3 scripts/check_nzbgeek_classical_lossless.py
```

Runs the live scan against NZBGeek category `3040`. Required env var: `NZB_GEEK_API_KEY`. Optional env vars: `OPENAI_API_KEY` and `OPENAI_MODEL`.

```bash
python3 -m py_compile scripts/check_nzbgeek_classical_lossless.py
```

Performs a fast syntax check before committing changes.

## Coding Style & Naming Conventions

Follow the existing Python style: 4-space indentation, type hints, dataclasses where they simplify structured results, and small helper functions for parsing and scoring. Prefer standard-library modules first; this script currently has no third-party dependencies. Use `UPPER_SNAKE_CASE` for constants, `snake_case` for functions and variables, and keep user-facing output terse because `SKILL.md` requires direct script output.

## Testing Guidelines

There is no formal test suite yet. When changing matching logic, validate with targeted local runs and confirm both paths:

1. Heuristic-only mode with `NZB_GEEK_API_KEY` set and no `OPENAI_API_KEY`.
2. LLM-assisted mode with both keys set.

Keep edge cases in mind: junk video posts, borderline crossover titles, and weak Discogs matches. If you add tests later, place them under `tests/` and mirror the script name, for example `tests/test_check_nzbgeek_classical_lossless.py`.

## Commit & Pull Request Guidelines

This directory is not currently a Git checkout, so no local commit history is available to infer conventions. Use short, imperative commit subjects such as `Tighten video junk filters` or `Refine Discogs confidence threshold`. PRs should describe the behavioral change, list any new environment requirements, and include a brief sample of before/after output when filtering logic changes.
