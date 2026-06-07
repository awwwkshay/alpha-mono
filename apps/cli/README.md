# clay-cli

Command-line tools for Clay apps.

## Usage

```bash
uv run clay init my-app
cd my-app
cp .env.example .env
uv run my-app
```

Use `--directory` to choose a parent directory and `--force` to overwrite generated
files in an existing app directory.

Start Clay Studio from a generated app directory:

```bash
uv run clay studio
```
