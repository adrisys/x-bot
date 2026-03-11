"""Tests for config parsing."""

import os
import unittest
from unittest.mock import patch

from bot.config import _parse_list, load_config


class ParseListTests(unittest.TestCase):
    def test_simple_csv(self) -> None:
        assert _parse_list("a,b,c") == ["a", "b", "c"]

    def test_strips_whitespace(self) -> None:
        assert _parse_list(" a , b , c ") == ["a", "b", "c"]

    def test_drops_empty_entries(self) -> None:
        assert _parse_list("a,,b,") == ["a", "b"]

    def test_empty_string(self) -> None:
        assert _parse_list("") == []


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
