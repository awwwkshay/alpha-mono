# Development Guide

## Setup

### Create and sync virtual environment

Sync all workspace packages and their dependencies into the root `.venv`:

```bash
uv sync --all-packages
```

### Activate virtual environment

```bash
source .venv/bin/activate
```

### Install pre-commit hooks

```bash
uv run pre-commit install
```

## Day-to-day

### Lint

```bash
uv run ruff check .
```

### Type check

```bash
uv run ty check
```

### Run hooks manually against all files

```bash
uv run pre-commit run --all-files
```

### Add a dependency to a specific package

```bash
uv add --package alpha-app <package>
```

### Add a dev dependency (root workspace)

```bash
uv add --dev <package>
```

## IDE setup

The workspace uses the root `.venv` as the shared interpreter. VS Code should pick it up automatically from `.vscode/settings.json`. If type errors appear for workspace packages, re-run `uv sync --all-packages` to ensure all dependencies are present.
