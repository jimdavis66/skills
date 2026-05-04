#!/usr/bin/env python3
"""Send a single NZB URL to SABnzbd."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


USER_AGENT = "codex-nzbgeek-classical-lossless/1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Queue an NZB URL in SABnzbd using the addurl API.",
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Direct NZB URL accessible by SABnzbd.",
    )
    parser.add_argument(
        "--name",
        help="Optional friendly job name for SABnzbd.",
    )
    return parser.parse_args()


def add_to_sabnzbd(server_url: str, api_key: str, nzb_url: str, job_name: str | None) -> str:
    params = {
        "mode": "addurl",
        "name": nzb_url,
        "apikey": api_key,
        "output": "json",
    }
    if job_name:
        params["nzbname"] = job_name

    request = urllib.request.Request(
        f"{server_url.rstrip('/')}/api?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("status") is True:
        ids = payload.get("nzo_ids")
        if isinstance(ids, list) and ids:
            return f"QUEUED {ids[0]}"
        return "QUEUED"

    error = payload.get("error") or payload.get("status")
    raise ValueError(f"SABNZBD add failed: {error}")


def main() -> int:
    args = parse_args()
    server_url = os.environ.get("SABNZBD_URL")
    api_key = os.environ.get("SABNZBD_API_KEY")

    if not server_url or not api_key:
        print("SABNZBD_URL and SABNZBD_API_KEY must be set", file=sys.stderr)
        return 1

    try:
        print(add_to_sabnzbd(server_url, api_key, args.url, args.name))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
