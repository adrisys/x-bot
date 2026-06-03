"""Tests for config parsing."""

import os
import unittest
from unittest.mock import patch

from bot.config import _parse_feeds, _parse_list, load_config


class ParseListTests(unittest.TestCase):
    def test_simple_csv(self) -> None:
        assert _parse_list("a,b,c") == ["a", "b", "c"]

    def test_strips_whitespace(self) -> None:
        assert _parse_list(" a , b , c ") == ["a", "b", "c"]

    def test_drops_empty_entries(self) -> None:
        assert _parse_list("a,,b,") == ["a", "b"]

    def test_empty_string(self) -> None:
        assert _parse_list("") == []


class ParseFeedsTests(unittest.TestCase):
    def test_parses_label_url_pairs(self) -> None:
        assert _parse_feeds("ar|https://a,es|https://b") == [
            ("ar", "https://a"),
            ("es", "https://b"),
        ]

    def test_strips_whitespace(self) -> None:
        assert _parse_feeds(" ar | https://a ") == [("ar", "https://a")]

    def test_skips_entries_without_separator(self) -> None:
        assert _parse_feeds("ar|https://a,bogus,es|https://b") == [
            ("ar", "https://a"),
            ("es", "https://b"),
        ]

    def test_empty_string(self) -> None:
        assert _parse_feeds("") == []


_REQUIRED_ENV = {
    "X_CONSUMER_KEY": "ck",
    "X_CONSUMER_SECRET": "cs",
    "X_ACCESS_TOKEN": "at",
    "X_ACCESS_TOKEN_SECRET": "ats",
    "LLM_API_KEY": "key",
}


class LoadConfigTests(unittest.TestCase):
    @patch.dict(os.environ, _REQUIRED_ENV, clear=True)
    def test_defaults(self) -> None:
        config = load_config()
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4o"
        assert config.post_interval_hours == 24
        assert config.dry_run is False

    @patch.dict(os.environ, {**_REQUIRED_ENV, "DRY_RUN": "true"}, clear=True)
    def test_dry_run(self) -> None:
        assert load_config().dry_run is True

    @patch.dict(os.environ, {**_REQUIRED_ENV, "POST_INTERVAL_HOURS": "12"}, clear=True)
    def test_interval(self) -> None:
        assert load_config().post_interval_hours == 12

    @patch.dict(os.environ, {**_REQUIRED_ENV, "LLM_PROVIDER": "anthropic"}, clear=True)
    def test_anthropic_default_model(self) -> None:
        assert load_config().llm_model == "claude-sonnet-4-20250514"


class TrendConfigTests(unittest.TestCase):
    @patch.dict(os.environ, _REQUIRED_ENV, clear=True)
    def test_trend_defaults(self) -> None:
        config = load_config()
        assert config.use_trends is False
        assert config.trend_include_hn is True
        assert config.trend_include_crypto is True
        assert config.trend_min_score == 50
        labels = [label for label, _ in config.trend_rss_feeds]
        assert "google-news-ar" in labels
        assert "cointelegraph" in labels

    @patch.dict(os.environ, {**_REQUIRED_ENV, "USE_TRENDS": "true"}, clear=True)
    def test_use_trends_enabled(self) -> None:
        assert load_config().use_trends is True

    @patch.dict(os.environ, {**_REQUIRED_ENV, "USE_TRENDS": "TRUE"}, clear=True)
    def test_use_trends_case_insensitive(self) -> None:
        assert load_config().use_trends is True

    @patch.dict(
        os.environ,
        {**_REQUIRED_ENV, "TREND_RSS_FEEDS": "rust|https://r,go|https://g"},
        clear=True,
    )
    def test_trend_rss_feeds_override(self) -> None:
        assert load_config().trend_rss_feeds == [
            ("rust", "https://r"),
            ("go", "https://g"),
        ]

    @patch.dict(os.environ, {**_REQUIRED_ENV, "TREND_MIN_SCORE": "250"}, clear=True)
    def test_trend_min_score_override(self) -> None:
        assert load_config().trend_min_score == 250

    @patch.dict(
        os.environ,
        {
            **_REQUIRED_ENV,
            "TREND_INCLUDE_HN": "false",
            "TREND_INCLUDE_CRYPTO": "false",
        },
        clear=True,
    )
    def test_trend_source_toggles_off(self) -> None:
        config = load_config()
        assert config.trend_include_hn is False
        assert config.trend_include_crypto is False
