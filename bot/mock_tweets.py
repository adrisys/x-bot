"""Mock viral tweets for testing the pipeline without X API credits."""

from bot.x_client import Tweet

MOCK_TWEETS = [
    Tweet(
        id="mock-001",
        text="Bitcoin isn't just an asset. It's the first time in history individuals can hold wealth that no government can seize. That's not finance — that's sovereignty.",
        author_username="naval",
        likes=12400,
        retweets=3200,
        lang="en",
    ),
    Tweet(
        id="mock-002",
        text="Cardano just processed 1M transactions in 24h with near-zero fees. But sure, keep telling me it's a ghost chain.",
        author_username="IOHK_Charles",
        likes=8700,
        retweets=2100,
        lang="en",
    ),
    Tweet(
        id="mock-003",
        text="El estado no te protege. Te cobra por existir y te castiga si produces demasiado. Eso no es un contrato social, es extorsión.",
        author_username="JMilei",
        likes=45000,
        retweets=11000,
        lang="es",
    ),
    Tweet(
        id="mock-004",
        text="España necesita una revolución fiscal. Bajar impuestos no es un regalo, es devolver lo que nunca debió tomarse.",
        author_username="Santi_ABASCAL",
        likes=6200,
        retweets=1800,
        lang="es",
    ),
    Tweet(
        id="mock-005",
        text="Passive income isn't passive. It's frontloaded work that compounds. Most people quit before the compounding starts.",
        author_username="naval",
        likes=32000,
        retweets=8500,
        lang="en",
    ),
    Tweet(
        id="mock-006",
        text="DeFi will eat traditional finance the same way the internet ate newspapers. Slowly, then all at once.",
        author_username="VitalikButerin",
        likes=15600,
        retweets=4300,
        lang="en",
    ),
    Tweet(
        id="mock-007",
        text="Austrian economics in one sentence: you can't print prosperity. Every attempt to do so steals from the future to subsidize the present.",
        author_username="saaborman",
        likes=4300,
        retweets=980,
        lang="en",
    ),
    Tweet(
        id="mock-008",
        text="La soberanía individual empieza cuando dejas de pedir permiso al estado para vivir tu vida.",
        author_username="liberpensador",
        likes=3100,
        retweets=720,
        lang="es",
    ),
]
