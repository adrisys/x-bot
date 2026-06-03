"""Configuration loaded from environment variables."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    # X API
    x_consumer_key: str
    x_consumer_secret: str
    x_access_token: str
    x_access_token_secret: str

    # LLM
    llm_provider: str  # "openai", "anthropic", or "grok"
    llm_api_key: str
    llm_model: str

    # Bot behaviour
    topics: list[str]
    persona: str
    post_interval_hours: int
    dry_run: bool

    # Trend discovery (free sources: RSS / HN / CoinGecko)
    use_trends: bool
    trend_rss_feeds: list[tuple[str, str]]
    trend_include_hn: bool
    trend_include_crypto: bool
    trend_min_score: int


def _parse_list(raw: str) -> list[str]:
    """Parse a comma-separated string into a list."""
    return [t.strip() for t in raw.split(",") if t.strip()]


def _parse_feeds(raw: str) -> list[tuple[str, str]]:
    """Parse comma-separated ``label|url`` pairs into (label, url) tuples.

    Entries without a ``|`` separator are skipped. URLs must not contain commas
    (the entry separator); Google News query URLs use ``+``/``%20``, so this is
    safe for the default lineup.
    """
    feeds: list[tuple[str, str]] = []
    for entry in raw.split(","):
        entry = entry.strip()
        if "|" not in entry:
            continue
        label, url = entry.split("|", 1)
        label, url = label.strip(), url.strip()
        if label and url:
            feeds.append((label, url))
    return feeds


_DEFAULT_PERSONA = (
    "You are writing from an X account. You are concise, original, and think in "
    "first principles. Vary your tone from tweet to tweet — sometimes contrarian, "
    "sometimes curious, sometimes witty, sometimes optimistic — so your timeline "
    "never feels repetitive or one-note. "
    "You write in either English or Spanish, but never mix both in the same tweet. "
    "Be quotable. No hashtags, no emojis unless truly fitting. "
    "Sound like a real person, not a bot."
)

_DEFAULT_TOPICS = (
"bitcoin,BTC,cardano,Cardano ADA,Charles Hoskinson,crypto,DeFi,web3,"
    "investing,Naval Ravikant,wealth creation,passive income,"
    "libertarian,sovereignty,Milei,Austrian economics,free market,anarcocapitalismo,"
    "política española,España,VOX,Abascal,impuestos,soberanía"
)

_DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "grok": "grok-3-latest",
}

# Default RSS lineup as ``label|url`` pairs. Google News search feeds cover the
# Spanish-language angles (Milei/Argentina, España) that Reddit previously
# supplied; Mises and Cointelegraph cover Austrian economics and crypto. Each
# becomes its own source family in pick_trend, so airtime stays balanced.
_DEFAULT_TREND_RSS_FEEDS = (
    "google-news-ar|https://news.google.com/rss/search?q=Milei&hl=es-419&gl=AR&ceid=AR:es-419,"
    "google-news-es|https://news.google.com/rss/search?q=Espa%C3%B1a&hl=es&gl=ES&ceid=ES:es,"
    "mises|https://mises.org/rss.xml,"
    "cointelegraph|https://cointelegraph.com/rss"
)


def load_config() -> Config:
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    default_model = _DEFAULT_MODELS.get(provider, "gpt-4o")

    return Config(
        # X API
        x_consumer_key=os.environ["X_CONSUMER_KEY"],
        x_consumer_secret=os.environ["X_CONSUMER_SECRET"],
        x_access_token=os.environ["X_ACCESS_TOKEN"],
        x_access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
        # LLM
        llm_provider=provider,
        llm_api_key=os.environ["LLM_API_KEY"],
        llm_model=os.environ.get("LLM_MODEL", default_model),
        # Bot
        topics=_parse_list(os.environ.get("TOPICS", _DEFAULT_TOPICS)),
        persona=os.environ.get("PERSONA", _DEFAULT_PERSONA),
        post_interval_hours=int(os.environ.get("POST_INTERVAL_HOURS", "24")),
        dry_run=os.environ.get("DRY_RUN", "false").lower() == "true",
        # Trends
        use_trends=os.environ.get("USE_TRENDS", "false").lower() == "true",
        trend_rss_feeds=_parse_feeds(
            os.environ.get("TREND_RSS_FEEDS", _DEFAULT_TREND_RSS_FEEDS)
        ),
        trend_include_hn=os.environ.get("TREND_INCLUDE_HN", "true").lower() == "true",
        trend_include_crypto=os.environ.get("TREND_INCLUDE_CRYPTO", "true").lower() == "true",
        trend_min_score=int(os.environ.get("TREND_MIN_SCORE", "50")),
    )
