"""X client for searching viral posts and publishing replies."""

import logging
from dataclasses import dataclass

import tweepy

from bot.config import Config

logger = logging.getLogger(__name__)


@dataclass
class Tweet:
    id: str
    text: str
    author_username: str
    likes: int
    retweets: int
    lang: str | None


class XClient:
    def __init__(self, config: Config) -> None:
        self._config = config

        self._reader = tweepy.Client(
            bearer_token=config.x_bearer_token,
            wait_on_rate_limit=True,
        )

        self._writer = tweepy.Client(
            consumer_key=config.x_consumer_key,
            consumer_secret=config.x_consumer_secret,
            access_token=config.x_access_token,
            access_token_secret=config.x_access_token_secret,
            wait_on_rate_limit=True,
        )

    def _build_search_query(self, query: str) -> str:
        exclusions = f"-from:{self._config.own_handle} -is:retweet -is:reply"
        full_query = (
            f"(({query}) {exclusions} lang:en) OR "
            f"(({query}) {exclusions} lang:es)"
        )
        return full_query[:512] if len(full_query) > 512 else full_query

    def search_viral_tweets(self, query: str, max_results: int = 50) -> list[Tweet]:
        """Search recent posts matching query and return those above thresholds."""
        full_query = self._build_search_query(query)

        try:
            response = self._reader.search_recent_tweets(
                query=full_query,
                max_results=min(max_results, 100),
                tweet_fields=["public_metrics", "author_id", "lang"],
                expansions=["author_id"],
                user_fields=["username"],
            )
        except tweepy.errors.TweepyException as e:
            logger.error("Search failed for query '%s': %s", query, e)
            return []

        if not response.data:
            return []

        users = {u.id: u.username for u in (response.includes.get("users") or [])}

        tweets = []
        for t in response.data:
            metrics = t.public_metrics or {}
            likes = metrics.get("like_count", 0)
            retweets = metrics.get("retweet_count", 0)

            if likes < self._config.min_likes and retweets < self._config.min_retweets:
                continue

            tweets.append(
                Tweet(
                    id=str(t.id),
                    text=t.text,
                    author_username=users.get(t.author_id, "unknown"),
                    likes=likes,
                    retweets=retweets,
                    lang=t.lang,
                )
            )

        tweets.sort(key=lambda tw: tw.likes + tw.retweets, reverse=True)
        return tweets

    def post_reply(self, tweet_id: str, text: str) -> str | None:
        """Publish a reply to the given post."""
        try:
            response = self._writer.create_tweet(
                text=text,
                in_reply_to_tweet_id=tweet_id,
            )
            new_id = str(response.data["id"])
            logger.info("Posted reply %s to post %s", new_id, tweet_id)
            return new_id
        except tweepy.errors.TweepyException as e:
            logger.error("Failed to reply to %s: %s", tweet_id, e)
            return None