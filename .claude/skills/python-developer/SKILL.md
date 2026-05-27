---
name: python-developer
description: A Python developer skilled in building and maintaining Python applications, writing clean and efficient code, and collaborating with cross-functional teams to deliver high-quality software solutions.
---

## Overview

The `python-developer` skill provides capabilities for writing, debugging, and maintaining Python code. It can assist with tasks such as:

- Writing Python functions and classes
- Debugging code and fixing errors
- Refactoring code for improved readability and performance
- Collaborating on code reviews and providing feedback
- Integrating with version control systems like Git
- Managing dependencies and virtual environments
- Writing unit tests and documentation
- Following best practices and coding standards

---

## Feature Development Workflow

When asked to build or implement a feature, the agent **must** follow this process in order. Do not skip steps or start writing code early.

### Step 1 — Analyse the request

Read the request carefully. Identify:

- What the feature does and what problem it solves
- What the expected inputs and outputs are
- Whether this is new functionality, an extension of existing functionality, or a change to existing behaviour
- Any constraints or non-functional requirements mentioned (performance, compatibility, etc.)

### Step 2 — Explore the codebase

Before asking any questions, use the available tools to understand the existing code:

- List and read all files and folders that are likely touched by this feature
- Identify the entry points, data models, contracts, and config schemas that are relevant
- Note what already exists that can be reused, extended, or must be changed
- Identify what new files or modules will need to be created and where they belong in the existing structure

Do not guess. Read the actual files.

### Step 3 — Ask clarifying questions

Read [`references/requirements_gathering.md`](references/requirements_gathering.md) before composing any questions. That file defines which categories to ask about, how to phrase questions precisely, what not to ask, and how to cap question count.

Key rules:
- Ask only what is genuinely ambiguous after reading the code — not what can be inferred from the request or the codebase
- Reference the actual code in your questions (file names, function names, existing patterns)
- Group questions by topic; aim for 3–6 total
- Show your assumption and ask for correction rather than asking open-ended questions

### Step 4 — Write the plan

Once questions are answered (or if no questions are needed), create a plan file at:

```text
.agent/temp/<task_name>_plan.md
```

Use a short, lowercase, hyphenated name for `task_name` that matches the feature (e.g. `streaming-tool-results_plan.md`).

The plan file must include:

```markdown
# Plan: <feature name>

## Summary
One paragraph describing what this feature does and why.

## Scope
- What is in scope
- What is explicitly out of scope

## Affected files
List every file that will be modified, and for each one what will change.

## New files
List every new file that will be created, with its path and purpose.

## Implementation steps
Ordered list of concrete steps. Each step should be small enough to verify independently.

## Open questions
Any remaining unknowns that could affect the implementation (if none, omit this section).
```

Show the plan to the user and wait for confirmation before writing any code.

### Step 5 — Refine the plan

Present the plan to the user and explicitly ask:

- Does this plan capture the full scope of what you want?
- Are there any steps you want to add, remove, or reorder?
- Any constraints or preferences not yet reflected?

**After every clarification or answer from the user — no matter how small — update the plan file immediately before asking the next question or continuing.** The plan file must always reflect the current agreed understanding. Never accumulate multiple clarifications and update the plan in bulk at the end.

Repeat the present → clarify → update loop until the user confirms the plan is final. Only move forward once you have explicit approval.

### Step 6 — Implement

Switch from plan mode to working mode. Announce this transition clearly to the user (e.g. "Plan finalised — starting implementation").

Work through the implementation steps from the plan in order:

- Complete one step at a time
- Keep changes focused — do not refactor unrelated code
- Do not add features or abstractions beyond what the plan specifies

### Step 7 — Verify

After all implementation steps are complete, run the full verification suite in this order:

1. **Tests** — run the test suite and confirm all tests pass
2. **Lint** — run `uv run ruff check .` and fix any reported issues
3. **Type check** — run `uv run ty check` and resolve all errors

If any check fails, fix the issue and re-run that check before moving on. Do not present the work as done until all three checks pass cleanly.

### Step 8 — Update documentation

After verification passes, update `README.md` and any affected files under `docs/` to reflect the changes introduced by the feature. Do not skip this step.

**Rules:**

- Only update sections that are directly affected by this feature — do not rewrite unrelated content
- If the feature adds a new concept, config field, step type, or public API, it must appear in `README.md` and `docs/architecture.md` (or a new doc file if warranted)
- If it changes existing behaviour, update the existing description — do not add a separate "new in vX" section
- Add or update a `Last updated: YYYY-MM-DD` timestamp at the bottom of every doc file you touch, on its own line (plain text, no italics)

**What to update based on what changed:**

| Change type                              | Update                                                              |
| ---------------------------------------- | ------------------------------------------------------------------- |
| New concept, class, or public interface  | Add to the Concepts table in `README.md` and the relevant section in `docs/architecture.md` |
| New config field or schema               | Update the relevant schema description in `docs/architecture.md`   |
| New filesystem or sandbox backend        | Add to the backends table in `docs/architecture.md`                |
| New workspace tool exposed to the LLM   | Add to the tools table in `docs/architecture.md`                   |
| Changed CLI or run command               | Update the Setup or Example section in `README.md`                 |
| New package under `packages/` or `apps/`| Add to the Packages table in `README.md` and the repo layout       |

### Step 9 — Write the work summary

Create a summary file at:

```text
.agent/temp/<task_name>_work_summary.md
```

The summary file must include:

```markdown
# Work Summary: <feature name>

## What was built
Concise description of the feature as implemented.

## Files changed
For each file: what was changed and why.

## Files created
For each new file: its path and purpose.

## Verification
- Tests: [ pass / fail — note any skipped or new tests added ]
- Lint: [ pass / fail ]
- Type check: [ pass / fail ]

## Docs updated
List each doc file updated and what was changed.

## Deviations from plan
Any places where the implementation differed from the plan, and why.

## Known limitations
Anything that was intentionally left out of scope or is known to be incomplete.
```

Present the summary to the user once written.

---

## General coding standards

All code must conform to the rules in [`references/python_code_style.md`](references/python_code_style.md). That file is the authoritative source for formatting, naming, type hints, error handling, async patterns, and comment style — read it before writing any code.

Key rules to keep top of mind:

- Follow existing patterns in the codebase — naming, file structure, import style
- Validate at system boundaries (user input, external APIs); trust internal code
- No comments explaining what the code does — only add a comment if the *why* is non-obvious
- No speculative abstractions — solve the problem at hand, not hypothetical future problems
- Prefer editing existing files over creating new ones unless a new module is clearly warranted
