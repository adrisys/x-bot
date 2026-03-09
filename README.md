# X Bot

Automated X bot that runs as a Kubernetes CronJob and publishes LLM-generated posts on a schedule. The codebase also supports reply/search workflows, but the production setup in this repository is currently configured for original post generation (`BOT_MODE=post`).

## What This Is

This project packages a small Python worker that:

- loads configuration from environment variables
- uses an LLM provider (`openai`, `anthropic`, or `grok`) to generate tweet text
- publishes to X using OAuth 1.0a credentials
- stores local run state in SQLite when needed
- runs well as a scheduled batch job rather than a permanent always-on service

In the currently deployed Kubernetes setup, the bot:

- runs as a real Docker image
- is executed by a Kubernetes `CronJob`
- posts twice a day in `Europe/Madrid`
- does **not** search X before posting
- mounts a PVC at `/data` for SQLite state

## Operating Modes

- `post` — generate and publish an original tweet
- `reply` — reply to a specific tweet URL/text provided via env vars
- `auto` — search X for candidate tweets, generate replies, and publish them

The repository's current Kubernetes config uses `BOT_MODE=post`.

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
- `X_BEARER_TOKEN` — X API Bearer Token (needed for search-based modes like `auto`)
- `X_CONSUMER_KEY` / `X_CONSUMER_SECRET` — X OAuth 1.0a consumer credentials
- `X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET` — X OAuth 1.0a user credentials (Read+Write)
- `LLM_API_KEY` — API key for your chosen LLM provider

### Optional
- `LLM_PROVIDER` — `openai` (default), `anthropic`, or `grok`
- `LLM_MODEL` — Override model name (defaults: `gpt-4o`, `claude-sonnet-4-20250514`, `grok-3-latest`)
- `BOT_MODE` — `post`, `reply`, or `auto` (default: `auto` in code; `post` in `k8s/configmap.yaml`)
- `OWN_HANDLE` — Your X handle without @ (default: `your_x_handle`)
- `TOPICS` — Comma-separated list of post/search topics
- `PERSONA` — System prompt describing your writing style
- `MIN_LIKES` — Minimum likes to consider a tweet viral in `auto` mode (default: `50`)
- `MIN_RETWEETS` — Minimum retweets in `auto` mode (default: `10`)
- `MAX_REPLIES_PER_RUN` — Max replies per execution in `auto` mode (default: `3`)
- `REPLY_TWEET_URL` / `REPLY_TWEET_TEXT` — required for `reply` mode
- `DRY_RUN` — Set to `true` to generate/log without posting (default: `false`)
- `MOCK_MODE` — Use simulated tweets instead of real X search in `auto` mode
- `DB_PATH` — Path to SQLite DB for tracking replies (default: `/data/replied_tweets.db`)

## Deploy to Kubernetes

This section describes the same deployment model now running in the cluster:

- Docker image-based workload
- Kubernetes namespace `x-bot`
- secret created from a local `.env` file
- ConfigMap for non-secret runtime settings
- PVC for SQLite state
- CronJob for scheduled execution

### 1. Build and push the Docker image

```bash
docker buildx build \
  --platform linux/amd64 \
  --provenance=false \
  -t your-registry/x-bot:latest \
  --push .
```

### 2. Update the image reference

Edit `k8s/cronjob.yaml` and replace `your-registry/x-bot:latest` with your actual image.

### 3. Prepare your local `.env`

Create a local `.env` file with your real credentials. Do **not** commit it.

Expected keys:

```bash
X_BEARER_TOKEN=...
X_CONSUMER_KEY=...
X_CONSUMER_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...
LLM_API_KEY=...
```

You can also include optional overrides such as `LLM_PROVIDER`, but the deployed setup in this repo keeps most runtime config in `k8s/configmap.yaml`.

### 4. Create the namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 5. Create the runtime secret from `.env`

This is the pattern used for the live cluster deployment, rather than committing real values into `k8s/secret.yaml`.

```bash
kubectl create secret generic x-bot-secrets \
  -n x-bot \
  --from-env-file=.env \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 6. Apply the Kubernetes manifests

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/cronjob.yaml
```

### 7. Verify the live configuration

```bash
kubectl get cronjob x-bot -n x-bot -o wide
kubectl get configmap x-bot-config -n x-bot -o yaml
```

### 8. Trigger a manual run

```bash
job="x-bot-manual-$(date +%s)"
kubectl create job --from=cronjob/x-bot -n x-bot "$job"
kubectl wait --for=condition=complete -n x-bot job/$job --timeout=240s || true
kubectl logs -n x-bot job/$job
```

### 9. Optional: follow the pod logs live

```bash
job="x-bot-manual-$(date +%s)"
kubectl create job --from=cronjob/x-bot -n x-bot "$job"
pod=""
while [ -z "$pod" ]; do
  pod=$(kubectl get pods -n x-bot -l job-name="$job" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
  [ -z "$pod" ] && sleep 2
done
kubectl logs -f -n x-bot "$pod"
```

### 10. Current production-like settings in this repo

The checked-in Kubernetes config currently matches this behavior:

- `BOT_MODE=post`
- `DRY_RUN=false`
- `MOCK_MODE=false`
- schedule: `09:17` and `18:43` in `Europe/Madrid`
- image: `adriannavarro/x-bot:latest` (replace if using your own registry)

## Architecture

- **Docker image** packages the Python app
- **CronJob** schedules execution twice daily
- **Job** is created for each scheduled or manual run
- **Pod** runs a single short-lived container and exits
- **ConfigMap** supplies non-secret runtime settings
- **Secret** supplies X and LLM credentials
- **PVC** persists SQLite state at `/data/replied_tweets.db`

## How the current deployed mode works

In the current checked-in config (`BOT_MODE=post`), each run:

- chooses one topic from `TOPICS`
- asks the configured LLM to generate an original tweet
- posts the generated tweet to X
- exits

It does **not** search X in this mode.

If you switch to `BOT_MODE=auto`, the bot will:

- search X for recent posts matching the configured topics
- filter by engagement thresholds
- generate replies
- publish replies

That mode can consume X search credits and is not the production configuration described above.

## Changing the schedule

Edit `k8s/cronjob.yaml`, then re-apply:

```bash
kubectl apply -f k8s/cronjob.yaml
```

## LLM Providers

| Provider | Model Default | API Base |
|----------|--------------|----------|
| OpenAI   | gpt-4o       | api.openai.com |
| Anthropic | claude-sonnet-4-20250514 | api.anthropic.com |
| Grok (xAI) | grok-3-latest | api.x.ai/v1 |

Switch providers by changing `LLM_PROVIDER` and `LLM_API_KEY`. No code changes needed.
