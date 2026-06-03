"""Tests for bot.trends — parsing, aggregation, and selection."""

from unittest.mock import patch

from bot import trends
from bot.trends import (
    Trend,
    fetch_coingecko_trending,
    fetch_hackernews,
    fetch_rss,
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


# ---------- fetch_rss ----------

def _rss_bytes(items: list[tuple[str, str]]) -> bytes:
    parts = ["<rss><channel>"]
    for title, link in items:
        parts.append(f"<item><title>{title}</title><link>{link}</link></item>")
    parts.append("</channel></rss>")
    return "".join(parts).encode("utf-8")


def test_fetch_rss_parses_items():
    body = _rss_bytes(
        [
            ("Milei recorta el gasto", "https://news.example/a"),
            ("España sube impuestos", "https://news.example/b"),
        ]
    )
    with patch.object(trends, "_fetch_bytes", return_value=body):
        result = fetch_rss("google-news-ar", "https://feed", limit=2)

    assert len(result) == 2
    assert result[0].title == "Milei recorta el gasto"
    assert result[0].source == "rss/google-news-ar"
    assert result[0].url == "https://news.example/a"
    # Scored by feed position: first item ranks above the second.
    assert result[0].score > result[1].score


def test_fetch_rss_respects_limit():
    body = _rss_bytes([(f"item {i}", f"https://x/{i}") for i in range(10)])
    with patch.object(trends, "_fetch_bytes", return_value=body):
        result = fetch_rss("mises", "https://feed", limit=3)

    assert [t.title for t in result] == ["item 0", "item 1", "item 2"]


def test_fetch_rss_returns_empty_on_fetch_failure():
    with patch.object(trends, "_fetch_bytes", return_value=None):
        assert fetch_rss("any", "https://feed") == []


def test_fetch_rss_returns_empty_on_parse_error():
    with patch.object(trends, "_fetch_bytes", return_value=b"not xml at all"):
        assert fetch_rss("any", "https://feed") == []


def test_fetch_rss_skips_empty_titles():
    body = _rss_bytes([("", "https://x/a"), ("  ", "https://x/b")])
    with patch.object(trends, "_fetch_bytes", return_value=body):
        assert fetch_rss("any", "https://feed") == []


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
    def fake_rss(label: str, url: str, limit: int = 10):
        return [
            Trend(title="Same Story", source=f"rss/{label}", score=100),
        ]

    def fake_hn(limit: int = 10):
        return [Trend(title="same story", source="hackernews", score=500)]

    def fake_cg():
        return []

    with patch.object(trends, "fetch_rss", side_effect=fake_rss), patch.object(
        trends, "fetch_hackernews", side_effect=fake_hn
    ), patch.object(trends, "fetch_coingecko_trending", side_effect=fake_cg):
        result = gather_trends(
            [("a", "https://a"), ("b", "https://b")],
            include_hn=True,
            include_crypto=True,
        )

    assert len(result) == 1
    assert result[0].score == 500
    assert result[0].source == "hackernews"


def test_gather_trends_sorted_by_score_desc():
    def fake_rss(label: str, url: str, limit: int = 10):
        return [
            Trend(title="low", source="rss/x", score=10),
            Trend(title="high", source="rss/x", score=900),
            Trend(title="mid", source="rss/x", score=500),
        ]

    with patch.object(trends, "fetch_rss", side_effect=fake_rss), patch.object(
        trends, "fetch_hackernews", return_value=[]
    ), patch.object(trends, "fetch_coingecko_trending", return_value=[]):
        result = gather_trends(
            [("x", "https://x")], include_hn=False, include_crypto=False
        )

    assert [t.title for t in result] == ["high", "mid", "low"]


def test_gather_trends_skips_disabled_sources():
    with patch.object(trends, "fetch_rss", return_value=[]) as r, patch.object(
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
