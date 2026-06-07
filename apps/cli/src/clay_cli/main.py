from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import typer


app = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Command-line tools for Clay apps.",
)


class InitError(RuntimeError):
    """Raised when an app cannot be initialized."""


@app.callback()
def callback() -> None:
    """Command-line tools for Clay apps."""


def _to_kebab_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").lower()
    if not name:
        raise InitError("App name must contain at least one letter or number.")
    return name


def _to_module_name(value: str) -> str:
    module_name = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip().lower())
    module_name = re.sub(r"_+", "_", module_name).strip("_")
    if not module_name or module_name[0].isdigit():
        module_name = f"app_{module_name}"
    if not module_name:
        raise InitError("App name must produce a valid Python module name.")
    return module_name


def _write_file(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise InitError(f"{path} already exists. Re-run with --force to overwrite it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _pyproject(app_name: str, module_name: str) -> str:
    return f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{app_name}"
version = "0.0.1"
description = "A Clay app"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "clay-app==0.0.1",
]

[dependency-groups]
dev = [
    "ruff>=0.15.14",
    "ty>=0.0.39",
]

[project.scripts]
{app_name} = "{module_name}.main:run"

[tool.clay]
app = "{module_name}.main:APP"

[tool.clay.studio]
mode = "production"
host = "127.0.0.1"
port = 3000
open_browser = true
client_host = "127.0.0.1"
client_port = 5173

[tool.ruff]
line-length = 88
target-version = "py314"
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "W", "C90"]
ignore = ["E203", "E501"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.ty]
python-version = "3.14"

[tool.ty.rules]
division-by-zero = "warn"
"""


def _main_py(app_name: str) -> str:
    return f'''from __future__ import annotations

import asyncio
from pathlib import Path

from clay_app import ClayApp
from clay_core import AppConfig, ObservabilityConfig


ENV_FILE = Path(__file__).parents[2] / ".env"

APP_CONFIG = AppConfig(
    name="{app_name}",
    env_file=ENV_FILE,
    observability=ObservabilityConfig(endpoint="http://localhost:4317"),
    agents={{}},
    workflows={{}},
    debug=True,
)

APP = ClayApp(config=APP_CONFIG)


async def run_app() -> None:
    async with APP:
        print("Clay app initialized.")


def run() -> None:
    asyncio.run(run_app())
'''


def _readme(app_name: str) -> str:
    return f"""# {app_name}

A Clay app generated with `clay init`.

## Usage

```bash
cp .env.example .env
uv run {app_name}
```

Open Clay Studio:

```bash
uv run clay studio
```
"""


def _init_py(app_name: str) -> str:
    return f'"""Generated Clay app package for {app_name}."""\n'


def _env_example() -> str:
    return """# Add local secrets here, then copy to .env.
# Studio keeps keys in sync and strips values from this example file.
"""


def _gitignore() -> str:
    return """.env
.venv/
__pycache__/
*.pyc
"""


def _vscode_settings() -> str:
    return """{
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    },
    "python.languageServer": "None",
    "ruff.enable": true,
    "ruff.lint.enable": true,
    "ty.disableLanguageServices": false,
    "ty.diagnosticMode": "workspace",
    "ty.importStrategy": "fromEnvironment",
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"
}
"""


def _clay_yaml(app_name: str) -> str:
    return f"""version: 1
app:
  name: {app_name}
agents: {{}}
workflows: {{}}
workspaces: {{}}
"""


def init_app(
    name: str,
    *,
    directory: Path | None = None,
    force: bool = False,
) -> Path:
    app_name = _to_kebab_name(name)
    module_name = _to_module_name(app_name)
    target_dir = (directory or Path.cwd()) / app_name

    if target_dir.exists() and any(target_dir.iterdir()) and not force:
        raise InitError(
            f"{target_dir} is not empty. Re-run with --force to overwrite files."
        )

    _write_file(
        target_dir / "pyproject.toml", _pyproject(app_name, module_name), force=force
    )
    _write_file(target_dir / "README.md", _readme(app_name), force=force)
    _write_file(target_dir / "clay.yaml", _clay_yaml(app_name), force=force)
    _write_file(target_dir / ".env.example", _env_example(), force=force)
    _write_file(target_dir / ".gitignore", _gitignore(), force=force)
    _write_file(
        target_dir / "src" / module_name / "__init__.py",
        _init_py(app_name),
        force=force,
    )
    _write_file(
        target_dir / "src" / module_name / "main.py", _main_py(app_name), force=force
    )
    _write_file(
        target_dir / ".vscode" / "settings.json", _vscode_settings(), force=force
    )

    return target_dir


@app.command()
def init(
    name: Annotated[str, typer.Argument(help="App name, for example 'my-app'.")],
    directory: Annotated[
        Path | None,
        typer.Option(
            "--directory",
            "-d",
            help="Parent directory for the new app. Defaults to the current directory.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Overwrite generated files if they already exist.",
        ),
    ] = False,
) -> None:
    """Initialize a new Clay app."""
    try:
        target_dir = init_app(name, directory=directory, force=force)
    except InitError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"Initialized Clay app at {target_dir}")


@app.command()
def studio(
    mode: Annotated[
        str | None,
        typer.Option(
            "--mode",
            help=(
                "Studio environment: development starts Vite with HMR; "
                "preproduction and production serve the built SPA."
            ),
        ),
    ] = None,
    dev: Annotated[
        bool,
        typer.Option("--dev", help="Shortcut for --mode development."),
    ] = False,
    host: Annotated[
        str | None,
        typer.Option("--host", help="Host interface for the Studio server."),
    ] = None,
    port: Annotated[
        int | None,
        typer.Option("--port", help="Port for the Studio server."),
    ] = None,
    app_ref: Annotated[
        str | None,
        typer.Option(
            "--app",
            help="Clay app reference, for example 'my_app.main:APP'.",
        ),
    ] = None,
    no_open: Annotated[
        bool,
        typer.Option("--no-open", help="Do not open Studio in a browser."),
    ] = False,
    client_host: Annotated[
        str | None,
        typer.Option(
            "--client-host", help="Host interface for the Studio client dev server."
        ),
    ] = None,
    client_port: Annotated[
        int | None,
        typer.Option("--client-port", help="Port for the Studio client dev server."),
    ] = None,
) -> None:
    """Start the local Clay Studio server."""
    from clay_studio_server import run_studio
    from clay_studio_server.project import ProjectError

    try:
        run_studio(
            mode="development" if dev else mode,
            host=host,
            port=port,
            app_ref=app_ref,
            open_browser=False if no_open else None,
            client_host=client_host,
            client_port=client_port,
        )
    except ProjectError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc


def main() -> None:
    app()


if __name__ == "__main__":
    main()
