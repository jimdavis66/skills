#!/usr/bin/env python3
"""Scan NZBGeek Audio/Lossless for recent classical posts."""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable


NZBGEEK_API_URL = "https://api.nzbgeek.info/api"
DISCOGS_SEARCH_URL = "https://api.discogs.com/database/search"
USER_AGENT = "codex-nzbgeek-classical-lossless/1.0"
OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
NOW = datetime.now(timezone.utc)
CUTOFF = NOW - timedelta(hours=24)
LLM_REVIEW_BATCH_SIZE = 25
LLM_MIN_CONFIDENCE = 0.78
LLM_BORDERLINE_CONFIDENCE = 0.60

COMPOSERS = {
    "albinoni", "allegri", "arensky", "bach", "bartok", "beethoven", "bellini",
    "berlioz", "bizet", "boccherini", "borodin", "brahms", "bruckner", "bruckner",
    "charpentier", "chopin", "copland", "corelli", "debussy", "delibes", "delius",
    "dohnanyi", "donizetti", "dvorak", "elgar", "faure", "franck", "gesualdo",
    "glazunov", "glinka", "grieg", "handel", "haydn", "holst", "hummel", "ives",
    "janacek", "khachaturian", "korngold", "lalo", "liszt", "lutoslawski", "mahler",
    "massenet", "mendelssohn", "messiaen", "monteverdi", "moszkowski", "mozart",
    "musorgsky", "offenbach", "orff", "pachelbel", "paganini", "penderecki",
    "pergolesi", "poulenc", "prokofiev", "puccini", "purcell", "rachmaninoff",
    "rameau", "ravel", "respighi", "rimsky", "rossini", "saint-saens", "satie",
    "scarlatti", "schoenberg", "schubert", "schumann", "shostakovich", "sibelius",
    "smetana", "strauss", "stravinsky", "suk", "svendsen", "szymanowski", "tallis", "tartini", "tchaikovsky",
    "telemann", "verdi", "vivaldi", "vaughan", "villa-lobos", "vivaldi", "wagner",
    "weber", "wolf", "wieniawski",
}

CLASSICAL_FORMS = {
    "symphony", "concerto", "sonata", "quartet", "quintet", "trio", "chamber",
    "orchestra", "orchestral", "opera", "requiem", "mass", "cantata", "prelude",
    "fugue", "nocturne", "etude", "suite", "overture", "overtures", "lieder", "oratorio",
    "motet", "partita", "rhapsody", "variations", "adagio", "waltz", "waltzes",
    "mazurka", "polka", "polkas", "march", "marches", "strings",
}

LABELS = {
    "deutsche grammophon", "decca", "bis", "chandos", "harmonia mundi", "naxos",
    "hyperion", "ecm", "telarc", "philips", "sony classical", "warner classics",
    "erato", "pentatone", "ondine", "linn", "alpha", "cpo", "channel classics",
}

PERFORMERS = {
    "karajan", "bernstein", "abbado", "solti", "barenboim", "gardiner", "argerich",
    "horowitz", "gould", "perahia", "pollini", "brendel", "uchida", "yo yo ma",
    "yo-yo ma", "mutter", "pavarotti", "callas",
}

COMPILATION_PHRASES = {
    "best loved classics", "best-loved classics", "classical favourites",
    "classical favorites", "greatest classical", "essential classics",
    "classical chill", "the best of classical", "ultimate classical",
    "classical masterworks",
}

VIDEO_JUNK_PATTERNS = [
    r"\b(?:x26[45]|h\.?26[45]|hevc|avc|hdr|dv|dolby vision)\b",
    r"\b(?:2160p|1080p|720p|480p|4k|uhd|bluray|bdrip|brrip|web[- ]?dl|webrip|hdrip|dvdrip)\b",
    r"\b(?:mkv|mp4|avi|xvid)\b",
    r"\b(?:s\d{1,2}e\d{1,2}|season \d+|episode \d+)\b",
    r"\b(?:concert film|live at|documentary)\b",
    r"\b(?:ebook|audiobook|game|software|flac music video)\b",
    r"\b(?:xxx|porn)\b",
]

STOPWORDS = {
    "the", "and", "for", "with", "from", "various", "artists", "artist", "disc",
    "cd", "sacd", "flac", "lossless", "remastered", "edition", "deluxe", "hires",
    "hi-res", "24bit", "24-bit", "192khz", "96khz", "stereo", "mono", "new", "a",
}

DISCOGS_NOISE_TOKENS = {
    "take", "proper", "repack", "readnfo", "proof", "promo", "bootleg",
}


@dataclass
class Match:
    title: str
    nzbgeek_url: str
    nzb_download_url: str | None
    discogs_url: str | None
    review_note: str | None = None


@dataclass
class LLMDecision:
    title: str
    is_classical: bool
    confidence: float
    reason: str
    needs_review: bool = False


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[-._/]+", " ", value)
    value = re.sub(r"[^a-z0-9+\- ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def title_tokens(value: str) -> set[str]:
    return {
        token for token in normalize_text(value).split()
        if len(token) > 2 and token not in STOPWORDS and not token.isdigit()
    }


def matches_any_phrase(title: str, phrases: Iterable[str]) -> bool:
    return any(phrase in title for phrase in phrases)


def contains_any_word(title: str, words: Iterable[str]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", title) for word in words)


def is_obvious_junk(title: str) -> bool:
    return any(re.search(pattern, title) for pattern in VIDEO_JUNK_PATTERNS)


def classical_score(title: str) -> int:
    score = 0
    composer_hits = sum(1 for word in COMPOSERS if re.search(rf"\b{re.escape(word)}\b", title))
    form_hits = sum(1 for word in CLASSICAL_FORMS if re.search(rf"\b{re.escape(word)}\b", title))
    label_hits = sum(1 for phrase in LABELS if phrase in title)
    performer_hits = sum(1 for phrase in PERFORMERS if phrase in title)
    compilation_hit = matches_any_phrase(title, COMPILATION_PHRASES)

    score += composer_hits * 4
    score += form_hits * 3
    score += label_hits * 4
    score += performer_hits * 4
    score += 5 if compilation_hit else 0
    score += 1 if "classical" in title else 0

    if composer_hits and (form_hits or performer_hits or label_hits):
        score += 4
    if performer_hits and form_hits:
        score += 2
    if label_hits and (composer_hits or performer_hits or form_hits):
        score += 2
    return score


def is_classical_title(raw_title: str) -> bool:
    title = normalize_text(raw_title)
    if not title or is_obvious_junk(title):
        return False

    score = classical_score(title)
    if score >= 7:
        return True

    if matches_any_phrase(title, COMPILATION_PHRASES):
        return True

    composer = contains_any_word(title, COMPOSERS)
    form = contains_any_word(title, CLASSICAL_FORMS)
    label = matches_any_phrase(title, LABELS)
    performer = matches_any_phrase(title, PERFORMERS)

    return (composer and form) or (composer and performer) or (label and form)


def should_skip_before_llm(raw_title: str) -> bool:
    title = normalize_text(raw_title)
    return not title or is_obvious_junk(title)


def request_json(url: str, params: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
    full_url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    request = urllib.request.Request(
        full_url,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def request_xml(url: str, params: dict[str, Any]) -> ET.Element:
    full_url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    request = urllib.request.Request(full_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return ET.fromstring(response.read())


def request_openai_response(api_key: str, payload: dict[str, Any]) -> Any:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_pubdate(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_json_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("item"), list):
            return [item for item in payload["item"] if isinstance(item, dict)]
        if isinstance(payload.get("item"), dict):
            return [payload["item"]]
        for key in ("channel", "rss"):
            if isinstance(payload.get(key), dict):
                items = normalize_json_items(payload[key])
                if items:
                    return items
    return []


def extract_attrs(attrs: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    if isinstance(attrs, dict):
        for key, value in attrs.items():
            if isinstance(value, (str, int, float)):
                result[str(key).lower()] = str(value)
    elif isinstance(attrs, list):
        for item in attrs:
            if not isinstance(item, dict):
                continue
            name = item.get("@attributes", {}).get("name") or item.get("name")
            value = item.get("@attributes", {}).get("value") or item.get("value")
            if name and value is not None:
                result[str(name).lower()] = str(value)
    return result


def result_page_url(item: dict[str, Any]) -> str | None:
    attrs = extract_attrs(item.get("attr") or item.get("attrs") or item.get("newznab:attr"))
    candidates = [
        item.get("comments"),
        attrs.get("comments"),
        item.get("guid"),
        item.get("link"),
        item.get("comments_url"),
    ]
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.startswith("http"):
            continue
        if any(flag in candidate for flag in ("/getnzb/", "/nzb/", "apikey=", "/api?")):
            continue
        return candidate
    return None


def nzb_download_url(item: dict[str, Any], api_key: str) -> str | None:
    link = item.get("link")
    if isinstance(link, str) and link.startswith("http"):
        return link

    guid = item.get("guid")
    if isinstance(guid, str) and guid.strip():
        if guid.startswith("http"):
            return guid
        return (
            f"{NZBGEEK_API_URL}?{urllib.parse.urlencode({'t': 'get', 'id': guid, 'apikey': api_key})}"
        )

    attrs = extract_attrs(item.get("attr") or item.get("attrs") or item.get("newznab:attr"))
    for key in ("guid", "downloadurl", "download_url"):
        value = attrs.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value
    return None


def xml_items_to_dicts(root: ET.Element) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        data: dict[str, Any] = {}
        attrs: list[dict[str, str]] = []
        for child in item:
            tag = child.tag.split("}")[-1]
            if tag == "attr":
                name = child.attrib.get("name")
                value = child.attrib.get("value")
                if name and value is not None:
                    attrs.append({"name": name, "value": value})
            else:
                data[tag] = (child.text or "").strip()
        if attrs:
            data["attr"] = attrs
        items.append(data)
    return items


def fetch_recent_nzbgeek_items(api_key: str) -> list[dict[str, Any]]:
    params = {
        "t": "search",
        "apikey": api_key,
        "cat": "3040",
        "o": "json",
        "extended": "1",
        "maxage": "1",
        "limit": "200",
    }
    try:
        payload = request_json(NZBGEEK_API_URL, params)
        items = normalize_json_items(payload)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        xml_root = request_xml(NZBGEEK_API_URL, {**params, "o": "xml"})
        items = xml_items_to_dicts(xml_root)

    recent: list[dict[str, Any]] = []
    for item in items:
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            continue
        pubdate = parse_pubdate(item.get("pubDate") or item.get("pubdate"))
        if pubdate and pubdate < CUTOFF:
            continue
        url = result_page_url(item)
        if not url:
            continue
        recent.append(item)
    return recent


def sanitize_discogs_query(title: str) -> str:
    cleaned = normalize_text(title)
    cleaned = re.sub(
        r"\b(?:flac|cd|sacd|24 bit|24bit|remastered|deluxe|lossless|web|take\d+)\b",
        " ",
        cleaned,
    )
    tokens = [
        token for token in cleaned.split()
        if token not in DISCOGS_NOISE_TOKENS
        and not re.fullmatch(r"(?:19|20)\d{2}", token)
        and not re.fullmatch(r"take\d+", token)
    ]
    return " ".join(tokens)


def extract_release_year(title: str) -> int | None:
    match = re.search(r"\b((?:19|20)\d{2})\b", normalize_text(title))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def build_discogs_queries(title: str) -> list[str]:
    base_query = sanitize_discogs_query(title)
    if not base_query:
        return []

    queries = [base_query]
    year = extract_release_year(title)
    if year:
        queries.append(f"{base_query} {year}")

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        if query not in seen:
            deduped.append(query)
            seen.add(query)
    return deduped


def discogs_score(query_title: str, result: dict[str, Any]) -> float:
    normalized_query = sanitize_discogs_query(query_title)
    normalized_result = normalize_text(str(result.get("title", "")))
    query_tokens = title_tokens(normalized_query)
    result_tokens = title_tokens(normalized_result)
    overlap = len(query_tokens & result_tokens)
    score = overlap * 2.5
    query_forms = query_tokens & CLASSICAL_FORMS
    result_forms = result_tokens & CLASSICAL_FORMS
    extra_result_tokens = result_tokens - query_tokens

    if normalized_result == normalized_query:
        score += 8
    if normalized_query and normalized_query in normalized_result:
        score += 4
    if query_tokens:
        score += (overlap / len(query_tokens)) * 4
    if query_forms and query_forms.issubset(result_forms):
        score += 2
    extra_forms = result_forms - query_forms
    score -= len(extra_forms) * 2.5
    score -= len(extra_result_tokens) * 0.35
    if "volume" in result_tokens and "volume" not in query_tokens:
        score -= 2

    query_year = extract_release_year(query_title)
    result_year_raw = result.get("year")
    try:
        result_year = int(str(result_year_raw))
    except (TypeError, ValueError):
        result_year = None
    if query_year and result_year:
        if query_year == result_year:
            score += 4
        else:
            score -= 4

    genre = " ".join(result.get("genre") or [])
    style = " ".join(result.get("style") or [])
    label = " ".join(result.get("label") or [])
    bundle = normalize_text(" ".join([genre, style, label]))

    if "classical" in bundle:
        score += 5
    if any(name in normalized_result for name in COMPOSERS):
        score += 3
    if any(name in normalized_result for name in PERFORMERS):
        score += 2
    if any(phrase in bundle for phrase in LABELS):
        score += 1.5

    return score


def find_discogs_match(title: str) -> str | None:
    scored_by_uri: dict[str, tuple[float, dict[str, Any]]] = {}
    for query in build_discogs_queries(title):
        params = {
            "q": query,
            "type": "release",
            "per_page": "10",
            "page": "1",
        }
        try:
            payload = request_json(DISCOGS_SEARCH_URL, params)
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            continue

        results = payload.get("results")
        if not isinstance(results, list) or not results:
            continue

        for result in results:
            if not isinstance(result, dict):
                continue
            uri = result.get("uri")
            if not isinstance(uri, str) or not uri.startswith("/"):
                continue
            score = discogs_score(title, result)
            if score <= 0:
                continue
            previous = scored_by_uri.get(uri)
            if previous is None or score > previous[0]:
                scored_by_uri[uri] = (score, result)

    scored = list(scored_by_uri.values())
    if not scored:
        return None

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    if best_score < 9:
        return None
    if second_score and (best_score - second_score) < 1.5 and best_score < 14:
        return None

    return f"https://www.discogs.com{best['uri']}"


def chunked(values: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start:start + size]


def extract_response_text(payload: dict[str, Any]) -> str | None:
    output = payload.get("output")
    if not isinstance(output, list):
        return None
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    return text
    return None


def build_llm_review_payload(model: str, titles: list[str]) -> dict[str, Any]:
    prompt = (
        "Review NZB release titles and decide whether each likely relates to classical music. "
        "Use conservative judgment. Mark crossover, soundtrack, spoken word, video, or ambiguous pop/jazz releases "
        "as not classical unless the title strongly indicates a classical release. "
        "Return one verdict for every title provided.\n\n"
        "Titles:\n" +
        "\n".join(f"- {title}" for title in titles)
    )
    return {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You classify music release titles. "
                            "Prefer precision over recall. "
                            "A title is classical only when the title itself strongly suggests classical repertoire, "
                            "classical performers, classical labels, or standard classical release packaging."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "classical_title_review",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "is_classical": {"type": "boolean"},
                                    "confidence": {"type": "number"},
                                    "reason": {"type": "string"},
                                    "needs_review": {"type": "boolean"},
                                },
                                "required": [
                                    "title",
                                    "is_classical",
                                    "confidence",
                                    "reason",
                                    "needs_review",
                                ],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["results"],
                    "additionalProperties": False,
                },
            }
        },
    }


def review_titles_with_llm(titles: list[str], api_key: str, model: str) -> dict[str, LLMDecision]:
    decisions: dict[str, LLMDecision] = {}
    for batch in chunked(titles, LLM_REVIEW_BATCH_SIZE):
        payload = request_openai_response(api_key, build_llm_review_payload(model, batch))
        response_text = extract_response_text(payload)
        if not response_text:
            raise ValueError("OpenAI response did not include output text")
        parsed = json.loads(response_text)
        results = parsed.get("results")
        if not isinstance(results, list):
            raise ValueError("OpenAI response did not include results")
        for result in results:
            if not isinstance(result, dict):
                continue
            title = result.get("title")
            if not isinstance(title, str) or title not in batch:
                continue
            confidence_raw = result.get("confidence")
            try:
                confidence = float(confidence_raw)
            except (TypeError, ValueError):
                confidence = 0.0
            decisions[title] = LLMDecision(
                title=title,
                is_classical=bool(result.get("is_classical")),
                confidence=max(0.0, min(confidence, 1.0)),
                reason=str(result.get("reason", "")).strip(),
                needs_review=bool(result.get("needs_review")),
            )
    return decisions


def llm_accepts_title(decision: LLMDecision | None) -> bool:
    if decision is None:
        return False
    if not decision.is_classical:
        return False
    if decision.needs_review:
        return False
    return decision.confidence >= LLM_MIN_CONFIDENCE


def llm_borderline_title(decision: LLMDecision | None) -> bool:
    if decision is None:
        return False
    if not decision.is_classical:
        return False
    if decision.confidence >= LLM_MIN_CONFIDENCE:
        return False
    return decision.needs_review or decision.confidence >= LLM_BORDERLINE_CONFIDENCE


def format_match(match: Match) -> str:
    parts = [match.title, match.nzbgeek_url]
    if match.nzb_download_url:
        parts.append(f"NZB_URL {match.nzb_download_url}")
    if match.discogs_url:
        parts.append(match.discogs_url)
    if match.review_note:
        parts.append(match.review_note)
    return " | ".join(parts)


def main() -> int:
    api_key = os.environ.get("NZB_GEEK_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    openai_model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    if not api_key:
        print("NZB_GEEK_API_KEY is not set", file=sys.stderr)
        return 1

    try:
        items = fetch_recent_nzbgeek_items(api_key)
    except urllib.error.URLError as exc:
        print(f"NZBGeek request failed: {exc}", file=sys.stderr)
        return 1
    except ET.ParseError as exc:
        print(f"NZBGeek response parse failed: {exc}", file=sys.stderr)
        return 1

    llm_candidates: list[tuple[str, str, str | None]] = []
    fallback_candidates: list[tuple[str, str, str | None]] = []
    seen_urls: set[str] = set()

    for item in items:
        title = str(item.get("title", "")).strip()
        url = result_page_url(item)
        download_url = nzb_download_url(item, api_key)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        if should_skip_before_llm(title):
            continue
        if openai_api_key:
            llm_candidates.append((title, url, download_url))
            continue
        if is_classical_title(title):
            fallback_candidates.append((title, url, download_url))

    matches: list[Match] = []
    llm_decisions: dict[str, LLMDecision] = {}
    llm_failed = False

    if openai_api_key and llm_candidates:
        try:
            llm_decisions = review_titles_with_llm(
                [title for title, _, _ in llm_candidates],
                openai_api_key,
                openai_model,
            )
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, ValueError) as exc:
            llm_failed = True
            print(f"OpenAI review failed, falling back to heuristics: {exc}", file=sys.stderr)

    for title, url, download_url in llm_candidates:
        if openai_api_key and not llm_failed:
            decision = llm_decisions.get(title)
            if llm_accepts_title(decision):
                matches.append(
                    Match(
                        title=title,
                        nzbgeek_url=url,
                        nzb_download_url=download_url,
                        discogs_url=find_discogs_match(title),
                    )
                )
                continue
            if llm_borderline_title(decision):
                note = f"REVIEW confidence={decision.confidence:.2f}"
                if decision.reason:
                    note = f"{note} reason={decision.reason}"
                matches.append(
                    Match(
                        title=title,
                        nzbgeek_url=url,
                        nzb_download_url=download_url,
                        discogs_url=find_discogs_match(title),
                        review_note=note,
                    )
                )
                continue
            continue
        if not is_classical_title(title):
            continue
        matches.append(
            Match(
                title=title,
                nzbgeek_url=url,
                nzb_download_url=download_url,
                discogs_url=find_discogs_match(title),
            )
        )

    for title, url, download_url in fallback_candidates:
        matches.append(
            Match(
                title=title,
                nzbgeek_url=url,
                nzb_download_url=download_url,
                discogs_url=find_discogs_match(title),
            )
        )

    if not matches:
        print("NO_REPLY")
        return 0

    for match in matches:
        print(format_match(match))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
