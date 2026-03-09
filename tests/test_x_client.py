import sys
import types
import unittest


fake_tweepy = types.SimpleNamespace(
    Client=object,
    errors=types.SimpleNamespace(TweepyException=Exception),
)
sys.modules.setdefault("tweepy", fake_tweepy)

from bot.x_client import XClient


class BuildSearchQueryTests(unittest.TestCase):
    def _client(self, own_handle: str = "your_x_handle") -> XClient:
        client = XClient.__new__(XClient)
        client._config = types.SimpleNamespace(own_handle=own_handle)
        return client

    def test_build_search_query_groups_each_language_branch(self) -> None:
        query = self._client()._build_search_query("bitcoin")

        self.assertEqual(
            query,
            "((bitcoin) -from:your_x_handle -is:retweet -is:reply lang:en) OR "
            "((bitcoin) -from:your_x_handle -is:retweet -is:reply lang:es)",
        )

    def test_build_search_query_caps_query_length(self) -> None:
        query = self._client("bot_account")._build_search_query("x" * 600)

        self.assertEqual(len(query), 512)


if __name__ == "__main__":
    unittest.main()