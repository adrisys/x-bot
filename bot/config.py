"""Configuration loaded from environment variables."""

import json
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # X API
    x_bearer_token: str
    x_consumer_key: str
    x_consumer_secret: str
    x_access_token: str
    x_access_token_secret: str

    # LLM
    llm_provider: str  # "openai", "anthropic", or "grok"
    llm_api_key: str
    llm_model: str

    # Bot behaviour
    bot_mode: str  # "auto", "post", or "reply"
    own_handle: str
    topics: list[str]
    persona: str
    min_likes: int
    min_retweets: int
    max_replies_per_run: int
    dry_run: bool
    mock_mode: bool

    # Manual reply mode
    reply_tweet_url: str
    reply_tweet_text: str

    # Storage
    db_path: str


def _parse_list(raw: str) -> list[str]:
    """Parse a JSON list or comma-separated string."""
    raw = raw.strip()
    if raw.startswith("["):
        return json.loads(raw)
    return [t.strip() for t in raw.split(",") if t.strip()]


_DEFAULT_PERSONA = (
    "You are writing from an X account. Your style is sharp, contrarian, and concise. "
    "You think in first principles and add a unique insight or reframe — you never just agree. "
    "You're comfortable mixing English and Spanish depending on the language of the tweet. "
    "Keep replies under 280 characters. Be quotable. No hashtags, no emojis unless truly fitting. "
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


def load_config() -> Config:
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    default_model = _DEFAULT_MODELS.get(provider, "gpt-4o")

    return Config(
        # X API
        x_bearer_token=os.environ["X_BEARER_TOKEN"],
        x_consumer_key=os.environ["X_CONSUMER_KEY"],
        x_consumer_secret=os.environ["X_CONSUMER_SECRET"],
        x_access_token=os.environ["X_ACCESS_TOKEN"],
        x_access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
        # LLM
        llm_provider=provider,
        llm_api_key=os.environ["LLM_API_KEY"],
        llm_model=os.environ.get("LLM_MODEL", default_model),
        # Bot
        bot_mode=os.environ.get("BOT_MODE", "auto").lower(),
        own_handle=os.environ.get("OWN_HANDLE", "your_x_handle"),
        topics=_parse_list(os.environ.get("TOPICS", _DEFAULT_TOPICS)),
        persona=os.environ.get("PERSONA", _DEFAULT_PERSONA),
        min_likes=int(os.environ.get("MIN_LIKES", "50")),
        min_retweets=int(os.environ.get("MIN_RETWEETS", "10")),
        max_replies_per_run=int(os.environ.get("MAX_REPLIES_PER_RUN", "3")),
        dry_run=os.environ.get("DRY_RUN", "false").lower() == "true",
        mock_mode=os.environ.get("MOCK_MODE", "false").lower() == "true",
        # Manual reply
        reply_tweet_url=os.environ.get("REPLY_TWEET_URL", ""),
        reply_tweet_text=os.environ.get("REPLY_TWEET_TEXT", ""),
        # Storage
        db_path=os.environ.get("DB_PATH", "/data/replied_tweets.db"),
    )
