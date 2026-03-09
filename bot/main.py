"""Main entry point — orchestrates the bot in different modes."""

import logging
import sys

from bot.config import load_config
from bot.llm_client import LLMClient
from bot.store import TweetStore
from bot.x_client import XClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _run_auto_mode(config, x_client, llm, store) -> None:
    """Auto mode: search for viral tweets and reply (requires Basic tier)."""
    if config.mock_mode:
        from bot.mock_tweets import MOCK_TWEETS
        logger.info("[MOCK MODE] Using %d simulated tweets", len(MOCK_TWEETS))
        candidates = [t for t in MOCK_TWEETS if not store.has_replied(t.id)]
    else:
        candidates = []
        for topic in config.topics:
            tweets = x_client.search_viral_tweets(topic)
            for tweet in tweets:
                if not store.has_replied(tweet.id):
                    candidates.append(tweet)

        # Deduplicate by tweet ID
        seen = set()
        unique = []
        for t in candidates:
            if t.id not in seen:
                seen.add(t.id)
                unique.append(t)
        candidates = unique

    # Sort by engagement and pick top N
    candidates.sort(key=lambda t: t.likes + t.retweets, reverse=True)
    targets = candidates[: config.max_replies_per_run]

    logger.info(
        "Found %d unique candidates, targeting top %d",
        len(candidates),
        len(targets),
    )

    for tweet in targets:
        logger.info(
            "Processing tweet %s by @%s (%d❤ %dRT): %s",
            tweet.id,
            tweet.author_username,
            tweet.likes,
            tweet.retweets,
            tweet.text[:80],
        )

        reply_text = llm.generate_reply(tweet)
        if not reply_text:
            logger.warning("LLM returned empty reply for tweet %s", tweet.id)
            continue

        if len(reply_text) > 280:
            reply_text = reply_text[:277] + "..."

        if config.dry_run:
            logger.info("[DRY RUN] Would reply to %s: %s", tweet.id, reply_text)
            store.mark_replied(tweet.id)
        else:
            new_id = x_client.post_reply(tweet.id, reply_text)
            if new_id:
                store.mark_replied(tweet.id)
                logger.info("Reply posted: %s", reply_text)
            else:
                logger.error("Failed to post reply to %s", tweet.id)


def run() -> None:
    config = load_config()
    logger.info(
        "Starting bot — mode=%s, provider=%s, model=%s, dry_run=%s",
        config.bot_mode,
        config.llm_provider,
        config.llm_model,
        config.dry_run,
    )

    x_client = XClient(config)
    llm = LLMClient(config)
    store = TweetStore(config.db_path)

    try:
        if config.bot_mode == "post":
            from bot.post_mode import run_post_mode
            run_post_mode(config, x_client, llm)

        elif config.bot_mode == "reply":
            from bot.reply_mode import run_reply_mode
            if not config.reply_tweet_url or not config.reply_tweet_text:
                logger.error(
                    "Reply mode requires REPLY_TWEET_URL and REPLY_TWEET_TEXT"
                )
                sys.exit(1)
            run_reply_mode(
                config, x_client, llm, store,
                config.reply_tweet_url, config.reply_tweet_text,
            )

        elif config.bot_mode == "auto":
            _run_auto_mode(config, x_client, llm, store)

        else:
            logger.error("Unknown BOT_MODE: %s", config.bot_mode)
            sys.exit(1)

    finally:
        store.close()

    logger.info("Run complete.")


if __name__ == "__main__":
    run()
