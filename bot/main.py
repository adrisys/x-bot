"""Main entry point — long-running process that tweets on a schedule."""

import logging
import random
import signal
import threading
from pathlib import Path

from bot.config import load_config
from bot.llm_client import LLMClient
from bot.x_client import XClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_shutdown = threading.Event()
_HEARTBEAT = Path("/tmp/x-bot-alive")
_MAX_ATTEMPTS = 2
_RETRY_DELAY = 30


def _handle_signal(signum: int, _frame: object) -> None:
    logger.info("Received signal %d, shutting down", signum)
    _shutdown.set()


def _touch_heartbeat() -> None:
    """Write a heartbeat file so the k8s liveness probe can verify we're alive."""
    _HEARTBEAT.touch()


def _build_prompt(topic: str) -> str:
    return (
        f"Write an original tweet about: {topic}\n\n"
        f"It should be a sharp, standalone take — the kind that gets quoted and shared. "
        f"Max 280 characters. Only output the tweet text, nothing else. "
        f"No hashtags unless absolutely natural. No emojis unless truly fitting. "
        f"Choose one language for the entire tweet — Spanish if the topic is Spanish-language, "
        f"otherwise English. Never mix languages in the same tweet."
    )


def _generate_tweet(llm: LLMClient, topic: str) -> str | None:
    """Generate a tweet, retrying once if it exceeds 280 characters."""
    for attempt in range(_MAX_ATTEMPTS):
        text = llm.generate(_build_prompt(topic))
        if not text:
            return None
        if len(text) <= 280:
            return text
        logger.warning(
            "Tweet too long (%d chars, attempt %d/%d), retrying",
            len(text), attempt + 1, _MAX_ATTEMPTS,
        )
    logger.error("Giving up — LLM could not produce a tweet under 280 chars")
    return None


def _post_cycle(config, x_client: XClient, llm: LLMClient) -> None:
    """Pick a topic, generate a tweet, and post it. Raises on failure."""
    topic = random.choice(config.topics)
    logger.info("Generating tweet on topic: %s", topic)

    tweet_text = _generate_tweet(llm, topic)
    if not tweet_text:
        raise RuntimeError("No tweet generated")

    if config.dry_run:
        logger.info("[DRY RUN] Would post: %s", tweet_text)
        return

    tweet_id = x_client.post_tweet(tweet_text)
    logger.info("Posted tweet %s: %s", tweet_id, tweet_text)


def run() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    config = load_config()
    interval_sec = config.post_interval_hours * 3600

    logger.info(
        "Starting bot — provider=%s, model=%s, interval=%dh, dry_run=%s",
        config.llm_provider,
        config.llm_model,
        config.post_interval_hours,
        config.dry_run,
    )

    x_client = XClient(config)
    llm = LLMClient(config)

    while not _shutdown.is_set():
        _touch_heartbeat()

        for attempt in range(_MAX_ATTEMPTS):
            try:
                _post_cycle(config, x_client, llm)
                break
            except Exception:
                if attempt < _MAX_ATTEMPTS - 1:
                    logger.exception(
                        "Post cycle failed (attempt %d/%d), retrying in %ds",
                        attempt + 1, _MAX_ATTEMPTS, _RETRY_DELAY,
                    )
                    if _shutdown.wait(timeout=_RETRY_DELAY):
                        break
                else:
                    logger.exception("All attempts failed, giving up for this cycle")

        jittered = interval_sec * random.uniform(0.85, 1.15)
        logger.info("Sleeping %.1f hours until next post", jittered / 3600)
        _shutdown.wait(timeout=jittered)

    _HEARTBEAT.unlink(missing_ok=True)
    logger.info("Shutdown complete.")


if __name__ == "__main__":
    run()
