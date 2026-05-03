# nzbgeek-classical-lossless

Small Python utility for scanning NZBGeek `Audio > Lossless` posts from the last 24 hours and surfacing likely classical releases.

## What it does

- Queries NZBGeek category `3040`
- Filters out obvious junk/misfiled video posts
- Keeps likely classical music matches
- Optionally uses OpenAI for extra classification
- Adds Discogs links when the match is strong

## Requirements

- Python 3
- `NZB_GEEK_API_KEY` (required)
- `OPENAI_API_KEY` (optional)
- `OPENAI_MODEL` (optional override)

## Usage

```bash
python3 scripts/check_nzbgeek_classical_lossless.py
```

## Optional: Send a result to SABnzbd

Set `SABNZBD_URL` and `SABNZBD_API_KEY`, then run:

```bash
python3 scripts/send_to_sabnzbd.py --url 'https://api.nzbgeek.info/api?t=get&id=...&apikey=...'
```
