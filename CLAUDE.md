# alpha-mono — Claude instructions

## Skill usage

When the user asks you to **build, implement, add, or change a feature** in this project — anything involving new code or behaviour — you **must** invoke the `/python-developer` skill via the Skill tool before doing any work. Do not start writing code until the skill's workflow has been followed.

The skill defines the full development process: analyse → explore → clarify → plan → implement → verify → docs → summary. Follow every step in order.

## Project layout

- `packages/core/` — `alpha_core` library (agents, workflows, workspace, evals)
- `apps/basic-app/` — example application built on `alpha_core`
- `docs/` — architecture and development docs

## Running checks

```bash
uv run ruff check .        # lint
uv run ty check            # type check
```
