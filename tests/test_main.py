"""Tests for tweet generation logic in main."""

import unittest
from unittest.mock import MagicMock

from bot.main import _build_prompt, _generate_tweet


class BuildPromptTests(unittest.TestCase):
    def test_contains_topic(self) -> None:
        prompt = _build_prompt("bitcoin")
        assert "bitcoin" in prompt

    def test_contains_char_limit(self) -> None:
        prompt = _build_prompt("anything")
        assert "280" in prompt

    def test_language_instructions(self) -> None:
        prompt = _build_prompt("anything")
        assert "Never mix languages" in prompt


class GenerateTweetTests(unittest.TestCase):
    def test_returns_short_tweet(self) -> None:
        llm = MagicMock()
        llm.generate.return_value = "Short tweet."
        assert _generate_tweet(llm, "topic") == "Short tweet."
        assert llm.generate.call_count == 1

    def test_retries_on_long_tweet(self) -> None:
        llm = MagicMock()
        llm.generate.side_effect = ["x" * 300, "Short enough."]
        assert _generate_tweet(llm, "topic") == "Short enough."
        assert llm.generate.call_count == 2

    def test_gives_up_after_max_attempts(self) -> None:
        llm = MagicMock()
        llm.generate.return_value = "x" * 300
        assert _generate_tweet(llm, "topic") is None
        assert llm.generate.call_count == 2

    def test_returns_none_on_empty(self) -> None:
        llm = MagicMock()
        llm.generate.return_value = None
        assert _generate_tweet(llm, "topic") is None

    def test_exactly_280_chars(self) -> None:
        llm = MagicMock()
        llm.generate.return_value = "a" * 280
        assert _generate_tweet(llm, "topic") == "a" * 280
