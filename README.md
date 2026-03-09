# X Reply Bot

Automated X bot that finds viral posts on your topics and publishes LLM-generated replies.

## Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Export required env vars
export X_BEARER_TOKEN="..."
export X_CONSUMER_KEY="..."
export X_CONSUMER_SECRET="..."
export X_ACCESS_TOKEN="..."
export X_ACCESS_TOKEN_SECRET="..."
export LLM_API_KEY="..."
export LLM_PROVIDER="openai"   # or "anthropic" or "grok"
export DRY_RUN="true"          # log replies without posting

# 3. Run
python -m bot.main
```

## Configuration

All config is via environment variables:

### Required
- `X_BEARER_TOKEN` — X API Bearer Token (for search)
- `X_CONSUMER_KEY` / `X_CONSUMER_SECRET` — X OAuth 1.0a consumer credentials
- `X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET` — X OAuth 1.0a user credentials (Read+Write)
- `LLM_API_KEY` — API key for your chosen LLM provider

### Optional
- `LLM_PROVIDER` — `openai` (default), `anthropic`, or `grok`
- `LLM_MODEL` — Override model name (defaults: `gpt-4o`, `claude-sonnet-4-20250514`, `grok-3-latest`)
- `OWN_HANDLE` — Your X handle without @ (default: `your_x_handle`)
- `TOPICS` — Comma-separated list of search keywords
- `PERSONA` — System prompt describing your reply style
- `MIN_LIKES` — Minimum likes to consider a tweet viral (default: `50`)
- `MIN_RETWEETS` — Minimum retweets (default: `10`)
- `MAX_REPLIES_PER_RUN` — Max replies per execution (default: `3`)
- `DRY_RUN` — Set to `true` to log replies without posting (default: `false`)
- `DB_PATH` — Path to SQLite DB for tracking replies (default: `/data/replied_tweets.db`)

## Deploy to Kubernetes

### 1. Build and push the Docker image

```bash
docker build -t your-registry/x-bot:latest .
docker push your-registry/x-bot:latest
```

### 2. Update the image reference

Edit `k8s/cronjob.yaml` and replace `your-registry/x-bot:latest` with your actual image.

### 3. Fill in secrets

Edit `k8s/secret.yaml` and replace all `REPLACE_ME` values with your actual API keys.

### 4. Apply manifests

```bash
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/cronjob.yaml
```

### 5. Test with a manual job

```bash
kubectl create job --from=cronjob/x-bot x-bot-test
kubectl logs -f job/x-bot-test
```

### 6. Go live

Once you're happy with dry-run output, set `DRY_RUN` to `"false"` in `k8s/configmap.yaml` and re-apply:

```bash
kubectl apply -f k8s/configmap.yaml
```

## Architecture

- **CronJob** runs every 15 minutes
- Searches X for recent tweets matching your topics
- Filters by engagement thresholds (likes/retweets)
- Skips tweets already replied to (tracked in SQLite)
- Generates replies via your chosen LLM with your persona prompt
- Posts replies via X API OAuth 1.0a

## LLM Providers

| Provider | Model Default | API Base |
|----------|--------------|----------|
| OpenAI   | gpt-4o       | api.openai.com |
| Anthropic | claude-sonnet-4-20250514 | api.anthropic.com |
| Grok (xAI) | grok-3-latest | api.x.ai/v1 |

Switch providers by changing `LLM_PROVIDER` and `LLM_API_KEY`. No code changes needed.
