# clay-mono — Codex instructions

## Skill usage

If the user asks to modify code, tests, configuration, or behavior in this repository, invoke the relevant development skill before editing files. For requests that are not feature changes (for example: debugging, explanation, code review, or question answering), do not invoke the development skills; answer directly.

If a required development skill cannot be invoked, stop and tell the user that the request cannot be completed under the current tool constraints; do not begin editing files.

**Skill selection rules:**

1. If the changed files are under Python or repository-tooling paths, use `/python-developer`.
2. If the changed files are under TypeScript/React/Vite paths (including `apps/studio-client/`), use `/typescript-developer`.
3. If both Python and TypeScript files are affected, invoke both skills and run all applicable checks from both toolchains; if the file set is unclear, ask the user to confirm the affected paths before editing.
4. If the request is docs-only or non-code, do not invoke these skills.

The skills define the full development process: analyse → explore → clarify → plan → implement → verify → docs → summary. Follow every step in order.

## Project layout

- `packages/core/` — `clay_core` library (agents, workflows, workspace, evals)
- `apps/examples/basic-app/` — example application built on `clay_core`
- `apps/studio-client/` — frontend TypeScript/React application
- `docs/` — architecture and development docs

## Running checks

Run the checks that match the files you changed: Python changes require `uv run ruff check .` and `uv run ty check`; TypeScript/frontend changes require `vp check` and `vp test`; mixed changes require all applicable checks.

```bash
uv run ruff check .        # lint
uv run ty check            # type check
vp check                   # TypeScript/frontend lint, format, and type checks
vp test                    # TypeScript/frontend tests
```
