#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
STUDIO_CLIENT = ROOT / "apps" / "studio-client"
STUDIO_CLIENT_DIST = STUDIO_CLIENT / "dist"
STUDIO_SERVER_DIST = (
    ROOT / "apps" / "studio-server" / "src" / "clay_studio_server" / "studio_dist"
)
DEFAULT_PACKAGES = (
    "clay-core",
    "clay-app",
    "clay-chat",
    "clay-studio-server",
    "clay-cli",
)
ENVIRONMENTS = ("development", "preproduction", "production")


def run(command: Sequence[str | Path], *, cwd: Path = ROOT) -> None:
    printable = " ".join(str(part) for part in command)
    print(f"$ {printable}")
    subprocess.run([str(part) for part in command], cwd=cwd, check=True)


def vp_command() -> str | Path:
    local_vp = STUDIO_CLIENT / "node_modules" / ".bin" / "vp"
    if local_vp.exists():
        return local_vp
    return "vp"


def build_studio_client(
    *,
    environment: str,
    skip_install: bool,
    skip_check: bool,
) -> None:
    if not STUDIO_CLIENT.exists():
        raise RuntimeError(f"Studio client not found at {STUDIO_CLIENT}")
    if not environment:
        raise RuntimeError("Build environment must not be empty.")

    vp = vp_command()
    if not skip_install:
        run([vp, "install"], cwd=STUDIO_CLIENT)
    if not skip_check:
        run([vp, "check"], cwd=STUDIO_CLIENT)
    run([vp, "run", "build", "--", "--mode", environment], cwd=STUDIO_CLIENT)


def copy_studio_dist() -> None:
    index_html = STUDIO_CLIENT_DIST / "index.html"
    if not index_html.exists():
        raise RuntimeError(
            f"Studio client build is missing {index_html}. "
            "Run the Studio client build before packaging."
        )

    if STUDIO_SERVER_DIST.exists():
        shutil.rmtree(STUDIO_SERVER_DIST)
    shutil.copytree(STUDIO_CLIENT_DIST, STUDIO_SERVER_DIST)

    packaged_index = STUDIO_SERVER_DIST / "index.html"
    if not packaged_index.exists():
        raise RuntimeError(f"Studio server dist is missing {packaged_index}")


def build_python_packages(packages: Sequence[str], *, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for package in packages:
        run(["uv", "build", "--package", package, "--out-dir", out_dir])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build publishable Python packages. The Studio client is built first "
            "and copied into clay-studio-server before wheels are produced."
        )
    )
    parser.add_argument(
        "--package",
        action="append",
        dest="packages",
        help="Package name to build. May be repeated. Defaults to core packages.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "dist",
        help="Directory for built distributions.",
    )
    parser.add_argument(
        "--environment",
        default="production",
        choices=ENVIRONMENTS,
        help="Studio client build environment passed to Vite as --mode.",
    )
    parser.add_argument(
        "--skip-studio-client",
        action="store_true",
        help="Do not rebuild or copy the Studio client before Python packages.",
    )
    parser.add_argument(
        "--skip-studio-install",
        action="store_true",
        help="Do not run `vp install` before building the Studio client.",
    )
    parser.add_argument(
        "--skip-studio-check",
        action="store_true",
        help="Do not run `vp check` before building the Studio client.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    packages = tuple(args.packages or DEFAULT_PACKAGES)

    if not args.skip_studio_client:
        build_studio_client(
            environment=args.environment,
            skip_install=args.skip_studio_install,
            skip_check=args.skip_studio_check,
        )
        copy_studio_dist()

    build_python_packages(packages, out_dir=args.out_dir)


if __name__ == "__main__":
    main()
