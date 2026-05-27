# Python Code Style Guide

## Formatting

Enforced by `ruff` (`ruff.toml` in the repo root). Key settings:

- Line length: **88 characters** (`line-length = 88`)
- Target Python version: **3.14** (`target-version = "py314"`)
- Indentation: **4 spaces** (no tabs)
- Do not manually adjust whitespace that ruff controls — run `uv run ruff format .` to format

### Enabled lint rules

| Rule set | Covers                                    |
| -------- | ----------------------------------------- |
| `E`      | pycodestyle errors                        |
| `F`      | Pyflakes (unused imports, undefined names)|
| `W`      | pycodestyle warnings                      |
| `C90`    | McCabe complexity                         |

### Ignored rules

- `E203` — whitespace before `:` (conflicts with ruff format)
- `E501` — line too long (handled by the formatter)
- `F401` in `__init__.py` — unused imports are allowed in package init files

## Imports

- Standard library → third-party → first-party, each group separated by a blank line
- No wildcard imports (`from module import *`)
- Use `from __future__ import annotations` at the top of files that use forward references in type hints
- Place imports used only for type checking inside `if TYPE_CHECKING:` blocks

```python
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from alpha_core.schemas.app_config import AppConfig

if TYPE_CHECKING:
    from alpha_core.domain.workspace.workspace import Workspace
```

## Naming

| Kind                  | Convention          | Example                    |
| --------------------- | ------------------- | -------------------------- |
| Modules               | `snake_case`        | `local_file_system.py`     |
| Classes               | `PascalCase`        | `LocalFileSystem`          |
| Functions / methods   | `snake_case`        | `read_file`                |
| Variables             | `snake_case`        | `base_path`                |
| Constants             | `UPPER_SNAKE_CASE`  | `_MAX_TOOL_ITERATIONS`     |
| Private               | `_leading_underscore` | `_build_filesystem`      |
| Unused parameters     | `_name`             | `_context`                 |
| Type variables        | `PascalCaseT` suffix | `InputT`, `OutputT`       |

## Type hints

- All public functions and methods must have complete type annotations (parameters and return type)
- Use `X | Y` union syntax (not `Union[X, Y]`)
- Use `X | None` (not `Optional[X]`)
- Use built-in generics: `list[str]`, `dict[str, int]`, `tuple[int, ...]` (not `List`, `Dict`, `Tuple`)
- Use `collections.abc` for abstract types in annotations: `Callable`, `AsyncIterator`, `Awaitable`

```python
# correct
def read_file(self, path: str) -> str: ...
async def execute(self, input_data: dict, context: AppContext) -> dict: ...

# wrong
def read_file(self, path) -> str: ...
def get_name(self) -> Optional[str]: ...
```

## Functions and methods

- Prefer small, single-responsibility functions
- Use keyword-only arguments (`*`) for functions with more than two parameters where ordering would be ambiguous
- Avoid mutable default arguments — use `None` and assign inside the function body

```python
# correct
def __init__(self, *, working_directory: Path | None = None, timeout: int = 30) -> None:
    self._cwd = working_directory
    self._timeout = timeout

# wrong
def __init__(self, working_directory=None, env={}): ...
```

## Classes

- Use `@dataclass` for simple data holders with no behaviour
- Use Pydantic `BaseModel` for config and schema objects that need validation or serialisation
- Use plain classes for domain objects with behaviour (`Agent`, `Workspace`, `Workflow`)
- Always define `__all__` at the bottom of every module

## Error handling

- Raise specific exception types — never bare `raise Exception("...")`
- Define custom exception classes when the caller needs to distinguish the error type
- Only catch exceptions you can meaningfully handle; let others propagate
- Do not use exceptions for control flow

```python
# correct
class WorkflowStepInputError(Exception): ...
raise WorkflowStepInputError(step_name, schema, e)

# wrong
raise Exception("step failed")
try:
    result = do_thing()
except Exception:
    result = None
```

## Async

- Use `async def` for all I/O-bound operations
- Do not use `asyncio.run()` inside library code — only at application entry points
- Use `asyncio.gather()` for concurrent independent coroutines
- Do not mix sync and async code in the same call path without explicit bridging

## Comments and docstrings

- Do not add comments that explain *what* the code does — well-named identifiers do that
- Add a comment only when the *why* is non-obvious: a hidden constraint, a workaround, a subtle invariant
- One short line maximum — no multi-line comment blocks
- No docstrings on private functions or methods
- Public class docstrings: one sentence stating purpose, plus constructor args if non-obvious

```python
# correct — explains a non-obvious invariant
# Deduplication is intentional: a global workspace shared across agents must only be set up once.
self._workspaces: set[Workspace] = {w for w in agent_workspaces.values() if w is not None}

# wrong — just restates the code
# Iterate over all steps and execute each one
for step in self.steps.values():
    current_data = await step.execute(current_data, context)
```

## Type checking

Enforced by `ty` (`ty.toml` in the repo root). Key settings:

- Python version: **3.14**
- Extra source paths: `packages/core/src`, `apps/basic-app/src`

Run with `uv run ty check`. All errors must be resolved before a feature is considered done. The only accepted suppression is `# type: ignore[<code>]` on a specific line with a comment explaining why — blanket `# type: ignore` without a code is not allowed.

New packages added under `packages/` or `apps/` must have their `src/` directory added to `extra-paths` in `ty.toml`.

## Module layout

Each module should be structured in this order:

1. `from __future__ import annotations`
2. Standard library imports
3. Third-party imports
4. First-party imports
5. `if TYPE_CHECKING:` block (if needed)
6. Module-level constants
7. Helper functions (prefixed with `_`)
8. Classes
9. `__all__`

## `__all__`

Every module must define `__all__` listing only the public symbols it exports.

```python
__all__ = ["AlphaApp"]
```
