"""X client for publishing tweets."""

import logging

import tweepy

from bot.config import Config

logger = logging.getLogger(__name__)


class XClient:
    def __init__(self, config: Config) -> None:
        self._client = tweepy.Client(
            consumer_key=config.x_consumer_key,
            consumer_secret=config.x_consumer_secret,
            access_token=config.x_access_token,
            access_token_secret=config.x_access_token_secret,
        )

    def post_tweet(self, text: str) -> str:
        """Publish an original tweet. Raises on failure."""
        response = self._client.create_tweet(text=text)
        tweet_id = str(response.data["id"])
        logger.info("Posted tweet %s", tweet_id)
        return tweet_id
