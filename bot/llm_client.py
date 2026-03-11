"""LLM abstraction layer — supports OpenAI, Anthropic, and Grok (xAI)."""

import logging

from bot.config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified interface for generating text via different LLM providers."""

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

    def generate(self, prompt: str) -> str | None:
        """Generate text from the given prompt. Returns the text or None."""
        try:
            if self._provider in ("openai", "grok"):
                response = self._openai.chat.completions.create(
                    model=self._config.llm_model,
                    messages=[
                        {"role": "system", "content": self._config.persona},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=180,
                    temperature=0.9,
                )
                return response.choices[0].message.content.strip()

            elif self._provider == "anthropic":
                response = self._anthropic.messages.create(
                    model=self._config.llm_model,
                    system=self._config.persona,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=180,
                    temperature=0.9,
                )
                return response.content[0].text.strip()
        except Exception:
            logger.exception("LLM generation failed")
            return None
