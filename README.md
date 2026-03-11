# X Bot

A stateless Twitter/X bot that generates and posts original tweets using an LLM. Runs as a long-lived Kubernetes Deployment — one tweet per interval, no database, no read API calls.

## How It Works

Each cycle the bot:

1. Picks a random topic from a configured list
2. Sends it to an LLM (OpenAI, Anthropic, or Grok) with a persona prompt
3. Posts the generated tweet to X via OAuth 1.0a
4. Sleeps for `POST_INTERVAL_HOURS` (default: 24)

The only external calls are one LLM generation and one `create_tweet` per cycle.

## Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Export required env vars (or source .env)
export X_CONSUMER_KEY="..."
export X_CONSUMER_SECRET="..."
export X_ACCESS_TOKEN="..."
export X_ACCESS_TOKEN_SECRET="..."
export LLM_API_KEY="..."
export LLM_PROVIDER="openai"   # or "anthropic" or "grok"
export DRY_RUN="true"          # log tweet without posting

# 3. Run
python -m bot.main
```

Press `Ctrl+C` after the first tweet — the process shuts down gracefully.

## Configuration

All config is via environment variables.

### Required
- `X_CONSUMER_KEY` / `X_CONSUMER_SECRET` — X OAuth 1.0a consumer credentials
- `X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET` — X OAuth 1.0a user credentials (Read+Write)
- `LLM_API_KEY` — API key for your chosen LLM provider

### Optional
- `LLM_PROVIDER` — `openai` (default), `anthropic`, or `grok`
- `LLM_MODEL` — Override model name (defaults: `gpt-4o`, `claude-sonnet-4-20250514`, `grok-3-latest`)
- `TOPICS` — Comma-separated list of tweet topics
- `PERSONA` — System prompt describing your writing style
- `POST_INTERVAL_HOURS` — Hours between tweets (default: `24`)
- `DRY_RUN` — Set to `true` to generate/log without posting (default: `false`)

## Deploy to Kubernetes

### 1. Build and push the Docker image

```bash
docker buildx build --platform linux/amd64 -t your-registry/x-bot:latest --push .
```

### 2. Create the namespace and secrets

```bash
kubectl apply -f k8s/namespace.yaml

source .env && kubectl create secret generic x-bot-secrets -n x-bot \
  --from-literal=X_CONSUMER_KEY="$X_CONSUMER_KEY" \
  --from-literal=X_CONSUMER_SECRET="$X_CONSUMER_SECRET" \
  --from-literal=X_ACCESS_TOKEN="$X_ACCESS_TOKEN" \
  --from-literal=X_ACCESS_TOKEN_SECRET="$X_ACCESS_TOKEN_SECRET" \
  --from-literal=LLM_API_KEY="$LLM_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 3. Apply manifests

```bash
kubectl apply -f k8s/configmap.yaml -f k8s/deployment.yaml
```

### 4. Verify

```bash
kubectl logs -f -n x-bot deployment/x-bot
```

## Architecture

- **Deployment** — single-replica, long-running pod
- **ConfigMap** — non-secret runtime settings (topics, persona, interval)
- **Secret** — X and LLM credentials
- **Liveness probe** — file-based heartbeat at `/tmp/x-bot-alive`
- **Graceful shutdown** — handles SIGTERM, exits cleanly within seconds

No database, no persistent volumes, no read API calls.

## LLM Providers

- **OpenAI** — default model `gpt-4o`, base `api.openai.com`
- **Anthropic** — default model `claude-sonnet-4-20250514`, base `api.anthropic.com`
- **Grok (xAI)** — default model `grok-3-latest`, base `api.x.ai/v1`

Switch providers by changing `LLM_PROVIDER` and `LLM_API_KEY`. No code changes needed.
