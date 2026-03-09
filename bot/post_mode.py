"""Post mode — generates and posts original tweets based on persona and topics."""

import logging
import random

from bot.config import Config
from bot.llm_client import LLMClient
from bot.x_client import XClient

logger = logging.getLogger(__name__)


def _build_post_prompt(topic: str) -> str:
    return (
        f"Write an original tweet about: {topic}\n\n"
        f"It should be a sharp, standalone take — the kind that gets quoted and shared. "
        f"Max 280 characters. Only output the tweet text, nothing else. "
        f"No hashtags unless absolutely natural. No emojis unless truly fitting. "
        f"Vary between English and Spanish naturally based on the topic."
    )


def run_post_mode(config: Config, x_client: XClient, llm: LLMClient) -> None:
    """Generate and post an original tweet on a random topic."""
    topic = random.choice(config.topics)
    logger.info("Generating original tweet on topic: %s", topic)

    prompt = _build_post_prompt(topic)

    # Reuse LLM internals — we need to call with persona but no tweet context
    try:
        if llm._provider in ("openai", "grok"):
            from openai import OpenAI

            response = llm._openai.chat.completions.create(
                model=config.llm_model,
                messages=[
                    {"role": "system", "content": config.persona},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=100,
                temperature=0.9,
            )
            tweet_text = response.choices[0].message.content.strip()

        elif llm._provider == "anthropic":
            response = llm._anthropic.messages.create(
                model=config.llm_model,
                system=config.persona,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.9,
            )
            tweet_text = response.content[0].text.strip()

    except Exception:
        logger.exception("LLM generation failed for post mode")
        return

    if not tweet_text:
        logger.warning("LLM returned empty tweet")
        return

    if len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + "..."

    if config.dry_run:
        logger.info("[DRY RUN] Would post: %s", tweet_text)
    else:
        try:
            from tweepy import Client

            writer = Client(
                consumer_key=config.x_consumer_key,
                consumer_secret=config.x_consumer_secret,
                access_token=config.x_access_token,
                access_token_secret=config.x_access_token_secret,
            )
            response = writer.create_tweet(text=tweet_text)
            tweet_id = response.data["id"]
            logger.info("Posted tweet %s: %s", tweet_id, tweet_text)
        except Exception:
            logger.exception("Failed to post tweet")
