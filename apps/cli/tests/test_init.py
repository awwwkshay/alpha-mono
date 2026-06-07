from __future__ import annotations

import tomllib

import pytest
from typer.testing import CliRunner

from clay_cli.main import InitError, app, init_app


runner = CliRunner()


def test_init_app_creates_minimal_clay_app(tmp_path):
    app_dir = init_app("My Test App", directory=tmp_path)

    assert app_dir == tmp_path / "my-test-app"
    assert (
        (app_dir / "README.md").read_text(encoding="utf-8").startswith("# my-test-app")
    )
    assert (app_dir / ".env.example").exists()
    assert (app_dir / "clay.yaml").exists()
    assert (app_dir / "src" / "my_test_app" / "__init__.py").exists()

    main_py = (app_dir / "src" / "my_test_app" / "main.py").read_text(encoding="utf-8")
    assert 'name="my-test-app"' in main_py
    assert "ClayApp" in main_py

    pyproject = tomllib.loads((app_dir / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["name"] == "my-test-app"
    assert pyproject["project"]["scripts"]["my-test-app"] == "my_test_app.main:run"
    assert pyproject["project"]["dependencies"] == ["clay-app==0.0.1"]
    assert pyproject["tool"]["clay"]["app"] == "my_test_app.main:APP"
    assert pyproject["tool"]["clay"]["studio"]["mode"] == "production"
    assert pyproject["tool"]["clay"]["studio"]["host"] == "127.0.0.1"
    assert pyproject["tool"]["clay"]["studio"]["port"] == 3000
    assert pyproject["tool"]["clay"]["studio"]["open_browser"] is True
    assert pyproject["tool"]["clay"]["studio"]["client_host"] == "127.0.0.1"
    assert pyproject["tool"]["clay"]["studio"]["client_port"] == 5173


def test_init_app_refuses_non_empty_directory_without_force(tmp_path):
    app_dir = tmp_path / "demo"
    app_dir.mkdir()
    (app_dir / "existing.txt").write_text("keep me", encoding="utf-8")

    with pytest.raises(InitError, match="not empty"):
        init_app("demo", directory=tmp_path)

    assert (app_dir / "existing.txt").read_text(encoding="utf-8") == "keep me"


def test_cli_initializes_app(tmp_path):
    result = runner.invoke(app, ["init", "demo", "--directory", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "demo" / "pyproject.toml").exists()
    assert (tmp_path / "demo" / "clay.yaml").exists()
    assert "Initialized Clay app at" in result.stdout


def test_cli_includes_studio_command():
    result = runner.invoke(app, ["studio", "--help"])

    assert result.exit_code == 0
    assert "Start the local Clay Studio server" in result.stdout
