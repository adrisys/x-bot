# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `bot/`. Use `bot/main.py` as the entrypoint (long-running loop with tweet generation logic), `bot/config.py` for environment-driven settings, `bot/x_client.py` for the X write API, and `bot/llm_client.py` for LLM generation.

## Build, Test, and Development Commands
Install dependencies with `pip install -r requirements.txt`.
Run the bot locally with `python -m bot.main` (it will post once and then sleep).
Use `DRY_RUN=true python -m bot.main` to validate behavior without posting to X.
Build the container using the image destination documented by the current
deployment configuration. Production Kubernetes desired state and the pinned
image tag live in `../adrilab-infra/gitops/`; treat this repository's `k8s/`
manifests as a legacy/direct-deployment path.

## Coding Style & Naming Conventions
Target Python 3.12+ style, 4-space indentation, and standard-library-first imports. Follow the existing module pattern: `snake_case` for functions, variables, and modules, `PascalCase` for client classes, and concise docstrings on public functions. Keep configuration in environment variables rather than hardcoding secrets or deployment values. Match the current logging style with structured `logging` calls instead of `print()`.

## Testing Guidelines
Run the committed pytest suite with `pytest`. Add focused tests under `tests/`,
especially around config parsing and post generation, and name files
`test_<module>.py`. Use `DRY_RUN=true` for end-to-end validation that must not
post to X.

## Commit & Pull Request Guidelines
Use short, imperative commit subjects such as `Add post interval config`. Keep commits scoped to one change. Pull requests should include the behavior change, required env or manifest updates, validation steps, and sample logs when output changes are user-visible.

## Security & Configuration Tips
Never commit real credentials from `.env` or `k8s/secret.yaml`. Default new integrations to safe settings such as `DRY_RUN=true` until the end-to-end flow is verified.
