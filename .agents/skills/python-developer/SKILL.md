---
name: python-developer
description: Use for any Python code or behavior change in clay-mono, including building, implementing, adding, refactoring, fixing, moving packages, changing workspace configuration, or updating tests/docs tied to code behavior.
---

# Python Developer

Use this skill before any code or behavior change in `clay-mono`.

For docs-only or behavior-neutral changes, perform only the analysis and planning steps needed for the touched files; do not run lint, typecheck, or tests unless the changed files are executable or the user explicitly asks for verification.

Follow the workflow in order. Do not skip straight to implementation unless the change is limited to a single file and does not affect dependencies, workspace config, package layout, or user-facing commands.

You may skip the full analysis/exploration sequence only when the requested change is limited to one existing implementation file and does not alter dependencies, paths, workspace config, or tests.

## 1. Analyse

- Restate the concrete objective in implementation terms.
- Identify likely affected areas: `packages/core`, `packages/app`, `packages/chat`, `apps`, `docs`, root workspace config, lockfiles, tests, and scripts.
- If the requested change touches any directory not listed above, name each additional directory you inspected and state the specific dependency, import, or config link that makes it relevant before editing.
- If the requested file, package, or path does not exist in the repository, stop and report that the target path is missing before making any edits.
- Note risk level and expected verification. For package moves or dependency changes, include workspace, lockfile, type checker, linter, imports, documentation links, and command entry points in the impact surface.
- Check whether the worktree is dirty with `git status --short`. If a file that the request needs to change is already modified by the user, stop and ask for permission before editing it; do not overwrite unrelated user changes.
- If the target file is dirty or the target path does not exist, stop and ask the user for guidance before editing; do not guess a replacement path.

## 2. Explore

- Read before editing. Use `rg` and `rg --files` first for fast discovery.
- Inspect at least the implementation file, its nearest tests, and any directly related `pyproject.toml`, `uv.lock`, `ruff.toml`, `ty.toml`, or README file that could affect imports, commands, or package layout.
- Search for hard-coded paths, package names, import paths, console scripts, workspace members, test config, and docs links.
- Prefer structured config edits over ad hoc text replacement when practical.

## 3. Clarify

- If there is exactly one file or package path that can satisfy the request without changing other modules, proceed with that path. Treat a path as unique only when one repository file or package is the direct target of the requested change.
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

Run verification checks based on the change type:

1. **Always run** (all changes):

   ```bash
   uv run ruff check .
   uv run ty check
   ```

2. **If the change touches workspace paths, dependencies, or package configuration**:

   ```bash
   uv lock
   uv sync --all-packages
   ```

3. **If the touched package has tests**:

   ```bash
   uv run pytest packages/core/tests
   uv run pytest packages/chat/tests
   uv run pytest packages/app/tests
   ```

4. **If the change affects tooling files** (ruff.toml, ty.toml, pyproject.toml, or pre-commit config):
   ```bash
   uv run pre-commit run --all-files
   ```

**Error handling:** If any command fails, stop and report the exact command and error before doing anything else. Do not attempt recovery or further edits without explicit user permission.

**Verification guidance:**

- For dependency changes, prefer `uv add --package <package> <dependency>` or `uv add --dev <dependency>` over hand-editing dependency lists.
- For workspace membership or package path changes, inspect that editable sources point at the new paths after `uv lock`.

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
