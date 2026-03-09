"""LLM abstraction layer — supports OpenAI, Anthropic, and Grok (xAI)."""

import logging

from bot.config import Config
from bot.x_client import Tweet

logger = logging.getLogger(__name__)


def _build_user_prompt(tweet: Tweet) -> str:
    return (
        f"Reply to this tweet by @{tweet.author_username}:\n\n"
        f'"{tweet.text}"\n\n'
        f"Engagement: {tweet.likes} likes, {tweet.retweets} retweets.\n"
        f"Language: {tweet.lang or 'unknown'}.\n\n"
        f"Write a single reply tweet (max 280 chars). "
        f"Reply in the same language as the original tweet. "
        f"Only output the reply text, nothing else."
    )


class LLMClient:
    """Unified interface for generating tweet replies via different LLM providers."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._provider = config.llm_provider

        if self._provider in ("openai", "grok"):
            from openai import OpenAI

            base_url = (
                "https://api.x.ai/v1" if self._provider == "grok" else None
            )
            self._openai = OpenAI(api_key=config.llm_api_key, base_url=base_url)

        elif self._provider == "anthropic":
            from anthropic import Anthropic

            self._anthropic = Anthropic(api_key=config.llm_api_key)
        else:
            raise ValueError(f"Unknown LLM provider: {self._provider}")

    def generate_reply(self, tweet: Tweet) -> str | None:
        """Generate a reply for the given tweet. Returns the reply text or None."""
        user_prompt = _build_user_prompt(tweet)

        try:
            if self._provider in ("openai", "grok"):
                return self._generate_openai(user_prompt)
            elif self._provider == "anthropic":
                return self._generate_anthropic(user_prompt)
        except Exception:
            logger.exception("LLM generation failed for tweet %s", tweet.id)
            return None

    def _generate_openai(self, user_prompt: str) -> str:
        response = self._openai.chat.completions.create(
            model=self._config.llm_model,
            messages=[
                {"role": "system", "content": self._config.persona},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=100,
            temperature=0.9,
        )
        return response.choices[0].message.content.strip()

    def _generate_anthropic(self, user_prompt: str) -> str:
        response = self._anthropic.messages.create(
            model=self._config.llm_model,
            system=self._config.persona,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=100,
            temperature=0.9,
        )
        return response.content[0].text.strip()
