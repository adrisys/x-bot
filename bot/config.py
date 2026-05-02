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

    # Trend discovery (free sources: Reddit / HN / CoinGecko)
    use_trends: bool
    trend_subreddits: list[str]
    trend_include_hn: bool
    trend_include_crypto: bool
    trend_min_score: int


def _parse_list(raw: str) -> list[str]:
    """Parse a comma-separated string into a list."""
    return [t.strip() for t in raw.split(",") if t.strip()]


_DEFAULT_PERSONA = (
    "You are writing from an X account. Your style is sharp, contrarian, and concise. "
    "You think in first principles and add a unique insight or reframe — you never just agree. "
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

_DEFAULT_TREND_SUBREDDITS = (
    "CryptoCurrency,Bitcoin,cardano,argentina,espana,Austrian_Economics"
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
        trend_subreddits=_parse_list(
            os.environ.get("TREND_SUBREDDITS", _DEFAULT_TREND_SUBREDDITS)
        ),
        trend_include_hn=os.environ.get("TREND_INCLUDE_HN", "true").lower() == "true",
        trend_include_crypto=os.environ.get("TREND_INCLUDE_CRYPTO", "true").lower() == "true",
        trend_min_score=int(os.environ.get("TREND_MIN_SCORE", "50")),
    )
