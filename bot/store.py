"""SQLite store for tracking replied tweet IDs."""

import sqlite3
from pathlib import Path


class TweetStore:
    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS replied_tweets (
                tweet_id TEXT PRIMARY KEY,
                replied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    def has_replied(self, tweet_id: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM replied_tweets WHERE tweet_id = ?", (tweet_id,)
        )
        return cur.fetchone() is not None

    def mark_replied(self, tweet_id: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO replied_tweets (tweet_id) VALUES (?)", (tweet_id,)
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
