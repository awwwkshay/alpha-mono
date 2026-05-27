# Development Guide

## Setup

### Create and sync virtual environment

```bash
uv sync
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

### Run hooks manually against all files

```bash
uv run pre-commit run --all-files
```

### Add a dependency

```bash
uv add <package>
```

### Add a dev dependency

```bash
uv add --dev <package>
```

Last updated: 2026-05-27
