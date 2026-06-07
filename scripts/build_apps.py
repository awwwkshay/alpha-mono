#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///

from __future__ import annotations

import argparse

from build_packages import ENVIRONMENTS, build_studio_client, copy_studio_dist


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build app assets, including the Studio client distributable."
    )
    parser.add_argument(
        "--skip-studio-client",
        action="store_true",
        help="Do not rebuild or copy the Studio client.",
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
    parser.add_argument(
        "--environment",
        default="production",
        choices=ENVIRONMENTS,
        help="Studio client build environment passed to Vite as --mode.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.skip_studio_client:
        return
    build_studio_client(
        environment=args.environment,
        skip_install=args.skip_studio_install,
        skip_check=args.skip_studio_check,
    )
    copy_studio_dist()


if __name__ == "__main__":
    main()
