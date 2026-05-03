---
name: nzbgeek-classical-lossless
description: Check NZBGeek Audio/Lossless category 3040 for posts from the last 24 hours, filter for likely classical music releases, exclude obvious junk or misfiled video posts, and return concise match lines with NZBGeek result links, direct NZB URLs, and strong Discogs release links when available. If the user explicitly asks to send one result to SABnzbd, use the reported NZB URL with scripts/send_to_sabnzbd.py plus SABNZBD_URL and SABNZBD_API_KEY. Use this when the user wants a current NZBGeek classical-lossless scan or a terse classical release roundup from the last day.
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
python3 scripts/send_to_sabnzbd.py --url 'https://api.nzbgeek.info/api?t=get&id=...&apikey=...'
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
9. If the user wants SABnzbd delivery, pass the chosen `NZB_URL` value to `scripts/send_to_sabnzbd.py`.

## Output Rules

- Return the script output directly.
- If the script prints `NO_REPLY`, respond with exactly `NO_REPLY`.
- Keep the response concise.
- Do not add commentary around the results.
- Preserve the `NZB_URL ...` field in the response so the user can choose a specific result later.

## Notes

- Prefer the NZBGeek comments or result page when available; do not prefer direct download links.
- Discogs links are optional and should be omitted when the match is weak or ambiguous.
- `OPENAI_MODEL` is optional and defaults inside the script if not provided.
- `SABNZBD_URL` and `SABNZBD_API_KEY` are only required for `scripts/send_to_sabnzbd.py`.
- `scripts/send_to_sabnzbd.py` uses SABnzbd's `addurl` API, so SABnzbd must be able to reach the supplied `NZB_URL`.
