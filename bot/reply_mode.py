"""Manual reply mode — provide a tweet URL and text, bot generates and posts a reply."""

import logging
import re

from bot.config import Config
from bot.llm_client import LLMClient
from bot.store import TweetStore
from bot.x_client import Tweet, XClient

logger = logging.getLogger(__name__)


def _parse_tweet_url(url: str) -> str | None:
    """Extract post ID from an X URL."""
    match = re.search(r"x\.com/.+/status/(\d+)", url)
    return match.group(1) if match else None


def _parse_author_from_url(url: str) -> str:
    """Extract username from an X URL."""
    match = re.search(r"x\.com/(\w+)/status/", url)
    return match.group(1) if match else "unknown"


def run_reply_mode(
    config: Config,
    x_client: XClient,
    llm: LLMClient,
    store: TweetStore,
    tweet_url: str,
    tweet_text: str,
) -> None:
    """Generate and post a reply to a manually provided tweet."""
    tweet_id = _parse_tweet_url(tweet_url)
    if not tweet_id:
        logger.error("Could not parse tweet ID from URL: %s", tweet_url)
        return

    author = _parse_author_from_url(tweet_url)

    if store.has_replied(tweet_id):
        logger.info("Already replied to tweet %s, skipping", tweet_id)
        return

    tweet = Tweet(
        id=tweet_id,
        text=tweet_text,
        author_username=author,
        likes=0,
        retweets=0,
        lang=None,
    )

    logger.info("Generating reply to tweet %s by @%s", tweet_id, author)
    reply_text = llm.generate_reply(tweet)

    if not reply_text:
        logger.warning("LLM returned empty reply")
        return

    if len(reply_text) > 280:
        reply_text = reply_text[:277] + "..."

    if config.dry_run:
        logger.info("[DRY RUN] Would reply to %s: %s", tweet_id, reply_text)
        store.mark_replied(tweet_id)
    else:
        new_id = x_client.post_reply(tweet_id, reply_text)
        if new_id:
            store.mark_replied(tweet_id)
            logger.info("Reply posted: %s", reply_text)
        else:
            logger.error("Failed to post reply to %s", tweet_id)
