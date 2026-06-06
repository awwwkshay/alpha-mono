---
name: python-developer
description: Use for any Python code or behavior change in alpha-mono, including building, implementing, adding, refactoring, fixing, moving packages, changing workspace configuration, or updating tests/docs tied to code behavior.
---

# Python Developer

Use this skill before any code or behavior change in `alpha-mono`.

If the user request is docs-only or does not change code behavior, use the same workflow only to the extent needed for the affected files; do not run code verification unless the change affects executable behavior.

Follow the workflow in order. Do not skip straight to implementation unless the change is limited to a single file and does not affect dependencies, workspace config, package layout, or user-facing commands.

You may skip the full analysis/exploration sequence only when the requested change is limited to one existing implementation file and does not alter dependencies, paths, workspace config, or tests.

## 1. Analyse

- Restate the concrete objective in implementation terms.
- Identify likely affected areas: `packages/core`, `packages/app`, `packages/chat`, `apps`, `docs`, root workspace config, lockfiles, tests, and scripts.
- If the request affects files outside the listed areas, explicitly name the additional directories you inspected and state why they are in scope before making changes.
- Note risk level and expected verification. For package moves or dependency changes, include workspace, lockfile, type checker, linter, imports, documentation links, and command entry points in the impact surface.
- Check whether the worktree is dirty with `git status --short`. Preserve unrelated user changes.

## 2. Explore

- Read before editing. Use `rg` and `rg --files` first for fast discovery.
- Inspect at least the implementation file, its nearest tests, and any directly related `pyproject.toml`, `uv.lock`, `ruff.toml`, `ty.toml`, or README file that could affect imports, commands, or package layout.
- Search for hard-coded paths, package names, import paths, console scripts, workspace members, test config, and docs links.
- Prefer structured config edits over ad hoc text replacement when practical.

## 3. Clarify

- If the request maps to exactly one implementation path in the current repo structure, proceed with that path.
- If two or more paths are plausible, ask the user before editing.
- Ask the user only when multiple valid interpretations would produce materially different behavior or risk data loss.
- If a required tool or named skill is unavailable, say so briefly and continue with the closest local workflow.

## 4. Plan

Before editing, state the specific files or file groups to change and why.

Keep the plan scoped:

- implementation/config changes
- test or verification updates
- docs updates when paths, behavior, or user-facing commands change

Avoid unrelated refactors.

## 5. Implement

- Follow existing project patterns and naming.
- Keep package names stable unless the request explicitly asks to rename them.
- Update all path-sensitive config when files move:
  - root `pyproject.toml` workspace members and uv sources
  - package/app `pyproject.toml` files when relative paths or build metadata change
  - `ty.toml` `extra-paths`
  - docs and README links
  - scripts, CI, examples, and tests discovered by search
  - `uv.lock` after workspace/package path changes
- `ruff.toml` usually needs no change if checks run against `.`, but verify there are no explicit includes/excludes before deciding.
- Use `apply_patch` for manual file edits.
- Do not revert or overwrite unrelated user changes.
- Do not use destructive git commands unless the user explicitly requests them.

## 6. Verify

Always run:

```bash
uv run ruff check .
uv run ty check
```

Run these checks when the change affects workspace membership, package path changes, editable sources, or dependency configuration:

```bash
uv lock
uv sync --all-packages
```

Run these if the affected package or behavior has tests:

```bash
uv run pytest
uv run pytest packages/core/tests
uv run pytest packages/chat/tests
```

Run this if the change affects formatting, linting hooks, or repository-level tooling:

```bash
uv run pre-commit run --all-files
```

Verification guidance:

- For workspace membership or package path changes, run `uv lock` and inspect that editable sources point at the new paths.
- For dependency changes, prefer `uv add --package <package> <dependency>` or `uv add --dev <dependency>` over hand-editing dependency lists.
- If a verification command fails, report the exact command and error, state whether the failure is related to the change, and ask for permission before running `uv sync --all-packages` or other setup commands.
- If `uv`, `ruff`, `ty`, or `pytest` are unavailable, or if `uv sync --all-packages` is required but not permitted, stop after reporting the exact command and error and state which verification steps were skipped and why.

## 7. Docs

Update docs when a change affects:

- repo layout
- package/app locations
- setup or run commands
- public APIs or imports
- examples
- behavior users rely on

Keep documentation changes factual and scoped to the implemented change.

## 8. Summary

Final response should include:

- what changed
- important files touched
- verification commands run and their results
- any remaining risk or follow-up that is directly relevant

For reviews, lead with findings and file/line references instead of a change summary.
