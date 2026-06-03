"""Aggregate trending topics from free, public sources.

No API keys required. Sources:
  - Reddit JSON endpoints (per-subreddit `hot.json`)
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
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Reddit blocks generic/bot-like User-Agents (HTTP 403). It requires a
# descriptive, unique UA in the form `platform:appid:version (by /u/username)`.
# Override REDDIT_USER_AGENT in the environment to set the real account handle.
_USER_AGENT = os.environ.get(
    "REDDIT_USER_AGENT", "python:com.adrilab.x-bot:1.1 (by /u/adrilab)"
)
_TIMEOUT_SEC = 10


@dataclass(frozen=True)
class Trend:
    """A single trending item normalized across sources."""

    title: str
    source: str
    score: int
    url: str | None = None


def _fetch_json(url: str) -> dict | list | None:
    """GET a URL and parse JSON. Returns None on any failure."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SEC) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Rate limiting / anti-bot blocks are expected and best-effort; log a
        # one-line warning without a stack trace to avoid flooding the logs.
        logger.warning("Fetch blocked (HTTP %s) for %s", exc.code, url)
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        logger.exception("Failed to fetch %s", url)
        return None


def fetch_reddit(subreddit: str, limit: int = 10) -> list[Trend]:
    """Fetch hot posts from a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    data = _fetch_json(url)
    if not isinstance(data, dict):
        return []

    trends: list[Trend] = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        if post.get("stickied") or post.get("over_18"):
            continue
        title = (post.get("title") or "").strip()
        if not title:
            continue
        permalink = post.get("permalink") or ""
        trends.append(
            Trend(
                title=title,
                source=f"reddit/r/{subreddit}",
                score=int(post.get("score", 0)),
                url=f"https://reddit.com{permalink}" if permalink else None,
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
    subreddits: list[str],
    include_hn: bool = True,
    include_crypto: bool = True,
    per_source_limit: int = 10,
) -> list[Trend]:
    """Pull from all configured sources and return a deduplicated flat list."""
    all_trends: list[Trend] = []

    for subreddit in subreddits:
        all_trends.extend(fetch_reddit(subreddit, limit=per_source_limit))

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
    thousands while Reddit/HN report raw upvotes/points), so weighting purely by
    score lets one source dominate every selection. Instead we pick a source
    family uniformly at random, then a trend within it weighted by score. This
    gives Reddit, Hacker News, and CoinGecko an equal shot regardless of their
    score magnitude, which keeps the posted content varied.
    """
    candidates = [t for t in trends if t.score >= min_score]
    if not candidates:
        return None

    by_family: dict[str, list[Trend]] = {}
    for trend in candidates:
        family = trend.source.split("/", 1)[0]  # "reddit/r/Bitcoin" -> "reddit"
        by_family.setdefault(family, []).append(trend)

    family = random.choice(list(by_family.keys()))
    group = by_family[family]
    weights = [max(1, t.score) for t in group]
    return random.choices(group, weights=weights, k=1)[0]
