"""Tests for bot.trends — parsing, aggregation, and selection."""

from unittest.mock import patch

from bot import trends
from bot.trends import (
    Trend,
    fetch_coingecko_trending,
    fetch_hackernews,
    fetch_reddit,
    gather_trends,
    pick_trend,
)


# ---------- _fetch_json error handling ----------

def test_fetch_json_returns_none_on_url_error():
    import urllib.error

    with patch.object(
        trends.urllib.request,
        "urlopen",
        side_effect=urllib.error.URLError("boom"),
    ):
        assert trends._fetch_json("https://example.com") is None


# ---------- fetch_reddit ----------

def _reddit_payload(posts: list[dict]) -> dict:
    return {"data": {"children": [{"data": p} for p in posts]}}


def test_fetch_reddit_parses_posts():
    payload = _reddit_payload(
        [
            {"title": "BTC ETF approved", "score": 1234, "permalink": "/r/Bitcoin/x/"},
            {"title": "Cardano news", "score": 99, "permalink": "/r/cardano/y/"},
        ]
    )
    with patch.object(trends, "_fetch_json", return_value=payload):
        result = fetch_reddit("Bitcoin", limit=2)

    assert len(result) == 2
    assert result[0].title == "BTC ETF approved"
    assert result[0].score == 1234
    assert result[0].source == "reddit/r/Bitcoin"
    assert result[0].url == "https://reddit.com/r/Bitcoin/x/"


def test_fetch_reddit_skips_stickied_and_nsfw():
    payload = _reddit_payload(
        [
            {"title": "Pinned mod post", "score": 50, "stickied": True},
            {"title": "NSFW post", "score": 100, "over_18": True},
            {"title": "Real post", "score": 200, "permalink": "/r/x/y/"},
        ]
    )
    with patch.object(trends, "_fetch_json", return_value=payload):
        result = fetch_reddit("any")

    assert [t.title for t in result] == ["Real post"]


def test_fetch_reddit_returns_empty_on_fetch_failure():
    with patch.object(trends, "_fetch_json", return_value=None):
        assert fetch_reddit("any") == []


def test_fetch_reddit_skips_empty_titles():
    payload = _reddit_payload([{"title": "", "score": 10}, {"title": "  ", "score": 5}])
    with patch.object(trends, "_fetch_json", return_value=payload):
        assert fetch_reddit("any") == []


# ---------- fetch_hackernews ----------

def test_fetch_hackernews_parses_top_stories():
    fetched = []

    def fake_fetch(url: str):
        fetched.append(url)
        if url.endswith("topstories.json"):
            return [101, 102]
        if url.endswith("/101.json"):
            return {"title": "AI takes over", "score": 500, "url": "https://x.com/a"}
        if url.endswith("/102.json"):
            return {"title": "Rust 2.0", "score": 300, "url": "https://x.com/b"}
        return None

    with patch.object(trends, "_fetch_json", side_effect=fake_fetch):
        result = fetch_hackernews(limit=2)

    assert [t.title for t in result] == ["AI takes over", "Rust 2.0"]
    assert all(t.source == "hackernews" for t in result)
    assert result[0].score == 500


def test_fetch_hackernews_returns_empty_when_ids_fail():
    with patch.object(trends, "_fetch_json", return_value=None):
        assert fetch_hackernews() == []


# ---------- fetch_coingecko_trending ----------

def test_fetch_coingecko_trending_parses_coins():
    payload = {
        "coins": [
            {"item": {"name": "Bitcoin", "symbol": "btc", "market_cap_rank": 1}},
            {"item": {"name": "ObscureCoin", "symbol": "obs", "market_cap_rank": 999}},
            {"item": {"name": "NoRank", "symbol": "nrk"}},  # missing rank
        ]
    }
    with patch.object(trends, "_fetch_json", return_value=payload):
        result = fetch_coingecko_trending()

    assert [t.title for t in result] == [
        "Bitcoin (BTC)",
        "ObscureCoin (OBS)",
        "NoRank (NRK)",
    ]
    # Higher-ranked coin (rank=1) should score higher than rank=999
    assert result[0].score > result[1].score
    # Missing rank falls back to a low score (rank=10_000 -> score=0)
    assert result[2].score == 0


# ---------- gather_trends ----------

def test_gather_trends_dedupes_by_lowercased_title_keeping_highest_score():
    def fake_reddit(subreddit: str, limit: int = 10):
        return [
            Trend(title="Same Story", source=f"reddit/r/{subreddit}", score=100),
        ]

    def fake_hn(limit: int = 10):
        return [Trend(title="same story", source="hackernews", score=500)]

    def fake_cg():
        return []

    with patch.object(trends, "fetch_reddit", side_effect=fake_reddit), patch.object(
        trends, "fetch_hackernews", side_effect=fake_hn
    ), patch.object(trends, "fetch_coingecko_trending", side_effect=fake_cg):
        result = gather_trends(["a", "b"], include_hn=True, include_crypto=True)

    assert len(result) == 1
    assert result[0].score == 500
    assert result[0].source == "hackernews"


def test_gather_trends_sorted_by_score_desc():
    def fake_reddit(subreddit: str, limit: int = 10):
        return [
            Trend(title="low", source="reddit/r/x", score=10),
            Trend(title="high", source="reddit/r/x", score=900),
            Trend(title="mid", source="reddit/r/x", score=500),
        ]

    with patch.object(trends, "fetch_reddit", side_effect=fake_reddit), patch.object(
        trends, "fetch_hackernews", return_value=[]
    ), patch.object(trends, "fetch_coingecko_trending", return_value=[]):
        result = gather_trends(["x"], include_hn=False, include_crypto=False)

    assert [t.title for t in result] == ["high", "mid", "low"]


def test_gather_trends_skips_disabled_sources():
    with patch.object(trends, "fetch_reddit", return_value=[]) as r, patch.object(
        trends, "fetch_hackernews", return_value=[]
    ) as h, patch.object(trends, "fetch_coingecko_trending", return_value=[]) as c:
        gather_trends([], include_hn=False, include_crypto=False)

    r.assert_not_called()
    h.assert_not_called()
    c.assert_not_called()


# ---------- pick_trend ----------

def test_pick_trend_filters_by_min_score():
    items = [
        Trend(title="low", source="x", score=5),
        Trend(title="high", source="x", score=500),
    ]
    # min_score=100 should always pick "high"
    for _ in range(10):
        picked = pick_trend(items, min_score=100)
        assert picked is not None
        assert picked.title == "high"


def test_pick_trend_returns_none_when_no_candidates():
    assert pick_trend([], min_score=0) is None
    assert pick_trend([Trend(title="x", source="s", score=1)], min_score=100) is None
