"""Aggregate trending topics from free, public sources.

No API keys required. Sources:
  - RSS feeds (Google News, Mises, Cointelegraph, …) via `<item><title>`
  - Hacker News Firebase API (`topstories.json`)
  - CoinGecko `/search/trending`

All fetches are best-effort: failures are logged and return empty lists, so
the caller can fall back to a static topic list.
"""

import json
import logging
import os
import random
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Descriptive User-Agent applied to all outbound trend fetches. A generic/bot
# UA gets some providers to block with HTTP 403, so we send a descriptive one.
# Override HTTP_USER_AGENT in the environment to change it.
_USER_AGENT = os.environ.get(
    "HTTP_USER_AGENT", "python:com.adrilab.x-bot:1.1 (by /u/x-bot)"
)
_TIMEOUT_SEC = 10

# RSS items carry no popularity score, so rank them by feed position: the first
# item scores _RSS_TOP_SCORE and each subsequent item drops by _RSS_SCORE_STEP
# (floored at 1). This keeps every feed above a typical min_score while letting
# the family-balancing in pick_trend treat each feed as its own source.
_RSS_TOP_SCORE = 100
_RSS_SCORE_STEP = 5


@dataclass(frozen=True)
class Trend:
    """A single trending item normalized across sources."""

    title: str
    source: str
    score: int
    url: str | None = None


def _fetch_bytes(url: str) -> bytes | None:
    """GET a URL and return the raw response body. Returns None on any failure."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SEC) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        # Rate limiting / anti-bot blocks are expected and best-effort; log a
        # one-line warning without a stack trace to avoid flooding the logs.
        logger.warning("Fetch blocked (HTTP %s) for %s", exc.code, url)
        return None
    except (urllib.error.URLError, TimeoutError):
        logger.exception("Failed to fetch %s", url)
        return None


def _fetch_json(url: str) -> dict | list | None:
    """GET a URL and parse JSON. Returns None on any failure."""
    body = _fetch_bytes(url)
    if body is None:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        logger.exception("Failed to parse JSON from %s", url)
        return None


def fetch_rss(label: str, url: str, limit: int = 10) -> list[Trend]:
    """Fetch item titles from an RSS feed, scored by feed position."""
    body = _fetch_bytes(url)
    if body is None:
        return []

    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        logger.exception("Failed to parse RSS from %s", url)
        return []

    trends: list[Trend] = []
    for index, item in enumerate(root.iter("item")):
        if index >= limit:
            break
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        link = (item.findtext("link") or "").strip()
        score = max(1, _RSS_TOP_SCORE - index * _RSS_SCORE_STEP)
        trends.append(
            Trend(
                title=title,
                source=f"rss/{label}",
                score=score,
                url=link or None,
            )
        )
    return trends


def fetch_hackernews(limit: int = 10) -> list[Trend]:
    """Fetch top stories from Hacker News."""
    ids = _fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not isinstance(ids, list):
        return []

    trends: list[Trend] = []
    for story_id in ids[:limit]:
        item = _fetch_json(
            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        )
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        if not title:
            continue
        trends.append(
            Trend(
                title=title,
                source="hackernews",
                score=int(item.get("score", 0)),
                url=item.get("url"),
            )
        )
    return trends


def fetch_coingecko_trending() -> list[Trend]:
    """Fetch the top trending coins from CoinGecko (last 24h)."""
    data = _fetch_json("https://api.coingecko.com/api/v3/search/trending")
    if not isinstance(data, dict):
        return []

    trends: list[Trend] = []
    for entry in data.get("coins", []):
        item = entry.get("item", {})
        name = item.get("name")
        symbol = (item.get("symbol") or "").upper()
        if not name:
            continue
        # Lower market_cap_rank == more established. Invert so higher score == hotter.
        rank = item.get("market_cap_rank") or 10_000
        score = max(0, 10_000 - int(rank))
        trends.append(
            Trend(
                title=f"{name} ({symbol})" if symbol else name,
                source="coingecko",
                score=score,
                url=None,
            )
        )
    return trends


def gather_trends(
    rss_feeds: list[tuple[str, str]],
    include_hn: bool = True,
    include_crypto: bool = True,
    per_source_limit: int = 10,
) -> list[Trend]:
    """Pull from all configured sources and return a deduplicated flat list."""
    all_trends: list[Trend] = []

    for label, url in rss_feeds:
        all_trends.extend(fetch_rss(label, url, limit=per_source_limit))

    if include_hn:
        all_trends.extend(fetch_hackernews(limit=per_source_limit))

    if include_crypto:
        all_trends.extend(fetch_coingecko_trending())

    # Dedupe by lowercased title, keeping the highest-scoring instance.
    by_title: dict[str, Trend] = {}
    for trend in all_trends:
        key = trend.title.lower()
        existing = by_title.get(key)
        if existing is None or trend.score > existing.score:
            by_title[key] = trend

    return sorted(by_title.values(), key=lambda t: t.score, reverse=True)


def pick_trend(trends: list[Trend], min_score: int = 0) -> Trend | None:
    """Pick a trend, balancing fairly across sources.

    Scores are not comparable across sources (CoinGecko derives scores in the
    thousands while HN reports raw points and RSS items are scored by feed
    position), so weighting purely by score lets one source dominate every
    selection. Instead we pick a source family uniformly at random, then a trend
    within it weighted by score. This gives each RSS feed, Hacker News, and
    CoinGecko an equal shot regardless of their score magnitude, which keeps the
    posted content varied.
    """
    candidates = [t for t in trends if t.score >= min_score]
    if not candidates:
        return None

    by_family: dict[str, list[Trend]] = {}
    for trend in candidates:
        # Each source string is its own family ("rss/google-news-ar",
        # "hackernews", "coingecko"), so every feed gets equal airtime.
        by_family.setdefault(trend.source, []).append(trend)

    family = random.choice(list(by_family.keys()))
    group = by_family[family]
    weights = [max(1, t.score) for t in group]
    return random.choices(group, weights=weights, k=1)[0]
