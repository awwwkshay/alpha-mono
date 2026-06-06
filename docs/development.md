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

## CI/CD

Pull requests and pushes to `main` run GitHub Actions CI:

```bash
uv sync --all-packages --frozen
uv run ruff check .
uv run ty check
uv run pytest
uv build --package alpha-core --out-dir dist
uv build --package alpha-app --out-dir dist
uv build --package alpha-chat --out-dir dist
uvx twine check dist/*
```

Publishing runs from `.github/workflows/cd.yml` when a GitHub release is
published. It builds and checks the three package distributions, uploads them as
a workflow artifact, then publishes to PyPI through Trusted Publishing.

Configure each PyPI project (`alpha-core`, `alpha-app`, and `alpha-chat`) with a
GitHub Trusted Publisher that points at this repository, workflow
`.github/workflows/cd.yml`, and environment `pypi`.

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
