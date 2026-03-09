# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `bot/`. Use `bot/main.py` as the entrypoint, `bot/config.py` for environment-driven settings, `bot/x_client.py` and `bot/llm_client.py` for external integrations, and `bot/store.py` for SQLite state. Deployment manifests live in `k8s/` (`configmap.yaml`, `secret.yaml`, `cronjob.yaml`, `pvc.yaml`). Runtime artifacts such as `replied_tweets.db` and `.env` are local-only and should not be treated as source.

## Build, Test, and Development Commands
Install dependencies with `pip install -r requirements.txt`.
Run the bot locally with `python -m bot.main`.
Use `DRY_RUN=true python -m bot.main` to validate behavior without posting to X.
Build the container with `docker build -t x-bot:latest .`.
Deploy manifests with `kubectl apply -f k8s/configmap.yaml -f k8s/secret.yaml -f k8s/pvc.yaml -f k8s/cronjob.yaml`.
Smoke-test the CronJob with `kubectl create job --from=cronjob/x-bot x-bot-test`.

## Coding Style & Naming Conventions
Target Python 3.12+ style, 4-space indentation, and standard-library-first imports. Follow the existing module pattern: `snake_case` for functions, variables, and modules, `PascalCase` for dataclasses and client classes, and concise docstrings on public functions. Keep configuration in environment variables rather than hardcoding secrets or deployment values. Match the current logging style with structured `logging` calls instead of `print()`.

## Testing Guidelines
There is no committed automated test suite yet. For changes, add focused `pytest` tests under a new `tests/` directory when logic can be isolated, especially around config parsing, reply selection, and store behavior. Name files `test_<module>.py`. Until test coverage exists, validate changes with `DRY_RUN=true` and, when relevant, `MOCK_MODE=true` to avoid hitting live APIs.

## Commit & Pull Request Guidelines
This workspace does not include `.git`, so local commit history is unavailable. Use short, imperative commit subjects such as `Add mock-mode reply filtering`. Keep commits scoped to one change. Pull requests should include the behavior change, required env or manifest updates, validation steps, and sample logs or screenshots when output changes are user-visible.

## Security & Configuration Tips
Never commit real credentials from `.env` or `k8s/secret.yaml`. Treat `replied_tweets.db` as local state, not fixture data. Default new integrations to safe settings such as `DRY_RUN=true` until the end-to-end flow is verified.
