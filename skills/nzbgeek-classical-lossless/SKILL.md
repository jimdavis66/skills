---
name: nzbgeek-classical-lossless
description: Check NZBGeek Audio/Lossless category 3040 for posts from the last 24 hours, filter for likely classical music releases, exclude obvious junk or misfiled video posts, and present concise numbered findings with NZBGeek result links, direct NZB URLs, and strong Discogs release links when available. After presenting findings, offer to send a selected result to SABnzbd; only queue a result when the user gives an unambiguous number, title, or direct NZB URL. Use scripts/send_to_sabnzbd.py plus SABNZBD_URL and SABNZBD_API_KEY for SABnzbd delivery. Use this when the user wants a current NZBGeek classical-lossless scan, a terse classical release roundup from the last day, or help choosing one result to download.
---

# NZBGeek Classical Lossless

Use this skill when the user wants a fresh scan of NZBGeek category `3040` (`Audio > Lossless`) for likely classical releases from the last 24 hours.

## Requirements

- Python 3
- `NZB_GEEK_API_KEY` is required for scanning NZBGeek.
- `OPENAI_API_KEY` is optional and enables extra classification through the OpenAI Responses API.
- `OPENAI_MODEL` is optional and overrides the script default model.
- `SABNZBD_URL` and `SABNZBD_API_KEY` are only required when sending a chosen result to SABnzbd.

## Workflow

1. Run:

```bash
python3 scripts/check_nzbgeek_classical_lossless.py
```

If the user explicitly asks to send one result to SABnzbd after reviewing the scan, run:

```bash
python3 scripts/send_to_sabnzbd.py --url 'https://api.nzbgeek.info/api?t=get&id=...&apikey=...' --name 'Release title'
```

2. The script reads `NZB_GEEK_API_KEY` from the environment and queries NZBGeek via the Newznab API.
3. It excludes obvious junk and likely misfiled video posts.
4. If `OPENAI_API_KEY` is available, it sends all non-junk candidates to the OpenAI Responses API for a structured classical-or-not review.
5. High-confidence classical titles are returned normally; borderline classical titles are returned with a trailing `REVIEW ...` note so they can be checked manually.
6. If `OPENAI_API_KEY` is not set, or the OpenAI request fails, it falls back to the local heuristic matcher:
   - major composer names
   - common classical forms
   - classical labels
   - notable conductors and performers
   - obvious compilation-style classical titles such as "best loved classics"
7. It queries the Discogs public API for each surviving match and only keeps Discogs links when the match is strong enough.
8. Each accepted output line includes an `NZB_URL ...` field containing the direct NZBGeek download URL.
9. Present accepted matches as a numbered shortlist so the user can choose a result for download.
10. If the user wants SABnzbd delivery, pass the chosen `NZB_URL` value to `scripts/send_to_sabnzbd.py`.

## Output Rules

- If the script prints `NO_REPLY`, respond with exactly `NO_REPLY`.
- If matches are found, present them as a numbered shortlist.
- Keep each result concise.
- For each result, include:
  - the release title
  - the NZBGeek result page link
  - the Discogs link when present
  - any trailing `REVIEW ...` note
  - the `NZB_URL ...` field, unless the user only asked for a human-readable summary
- After the numbered list, ask the user to reply with the number of the result they want sent to SABnzbd.
- Do not send a result to SABnzbd from the initial scan unless the user already gave an unambiguous title, number, or direct `NZB_URL`.
- If multiple results could match the user's request, ask them to choose by number.

## SABnzbd Handoff

When the user chooses a result by number, title, or direct `NZB_URL`:

1. Identify the exact selected result from the most recent scan.
2. Use its `NZB_URL` value, not the NZBGeek result page URL.
3. Run:

```bash
python3 scripts/send_to_sabnzbd.py --url '...' --name 'Release title'
```

4. Report only the SABnzbd result, for example `QUEUED ...`, or the error if queuing failed.
5. If `SABNZBD_URL` or `SABNZBD_API_KEY` is missing, say that SABnzbd is not configured and do not retry.

## Notes

- Prefer the NZBGeek comments or result page when available; do not prefer direct download links.
- Discogs links are optional and should be omitted when the match is weak or ambiguous.
- `OPENAI_MODEL` is optional and defaults inside the script if not provided.
- `SABNZBD_URL` and `SABNZBD_API_KEY` are only required for `scripts/send_to_sabnzbd.py`.
- `scripts/send_to_sabnzbd.py` uses SABnzbd's `addurl` API, so SABnzbd must be able to reach the supplied `NZB_URL`.
