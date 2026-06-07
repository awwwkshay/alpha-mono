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

## Docs after feature changes

After completing any feature change, **always ask the user** whether they want the docs updated to reflect the change. Do not update docs automatically without asking — the user may have their own docs workflow or prefer to batch doc changes separately.

The question should be specific, not generic. Name the feature and the docs location. For example:

> "Want me to update `docs/` to document the new chat interface endpoints and tool editor?"

If the user says yes, update only the docs that are directly affected by the change. Do not rewrite unrelated docs sections.

## Skill maintenance

After every prompt, ask: **"Is this fix or pattern general enough to apply every time a similar change is made?"**

- If **yes** — add the rule to the relevant skill file under `.agents/skills/` before finishing the response. Place it in the most specific skill that owns that domain (e.g. `typescript-developer/SKILL.md` for frontend patterns, `python-developer/SKILL.md` for backend patterns). Write the rule as a concrete "always do X" or "never do Y" instruction so future agents can apply it without re-deriving it.
- If **no** — skip; one-off fixes do not belong in skills.

**Criteria for adding to a skill:**

1. The rule would prevent a class of bugs or wasted iteration if it were known upfront.
2. The rule is not already covered by existing skill content.
3. The rule is applicable across multiple future tasks, not just the current one.

Examples of rules worth adding: naming conventions, type-system patterns, library integration patterns, required import sequences, API design constraints. Examples of rules NOT worth adding: task-specific logic, workarounds for a single third-party bug, ephemeral scaffold choices.

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
