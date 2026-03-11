# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `bot/`. Use `bot/main.py` as the entrypoint (long-running loop with tweet generation logic), `bot/config.py` for environment-driven settings, `bot/x_client.py` for the X write API, and `bot/llm_client.py` for LLM generation.

## Build, Test, and Development Commands
Install dependencies with `pip install -r requirements.txt`.
Run the bot locally with `python -m bot.main` (it will post once and then sleep).
Use `DRY_RUN=true python -m bot.main` to validate behavior without posting to X.
Build the container for the cluster with `docker buildx build --platform linux/amd64 -t adriannavarro/x-bot:latest --push .`.
Deploy manifests with `kubectl apply -f k8s/configmap.yaml -f k8s/deployment.yaml`.

## Coding Style & Naming Conventions
Target Python 3.12+ style, 4-space indentation, and standard-library-first imports. Follow the existing module pattern: `snake_case` for functions, variables, and modules, `PascalCase` for client classes, and concise docstrings on public functions. Keep configuration in environment variables rather than hardcoding secrets or deployment values. Match the current logging style with structured `logging` calls instead of `print()`.

## Testing Guidelines
There is no committed automated test suite yet. For changes, add focused `pytest` tests under a `tests/` directory when logic can be isolated, especially around config parsing and post generation. Name files `test_<module>.py`. Until test coverage exists, validate changes with `DRY_RUN=true`.

## Commit & Pull Request Guidelines
Use short, imperative commit subjects such as `Add post interval config`. Keep commits scoped to one change. Pull requests should include the behavior change, required env or manifest updates, validation steps, and sample logs when output changes are user-visible.

## Security & Configuration Tips
Never commit real credentials from `.env` or `k8s/secret.yaml`. Default new integrations to safe settings such as `DRY_RUN=true` until the end-to-end flow is verified.
