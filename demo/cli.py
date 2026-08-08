"""Command-line entry point for demo."""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demo",
        description="A full-featured modeless CLI code editor.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="files to open (created if they do not exist)",
    )
    parser.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help="path to a config file (default: ~/.config/demo/config.toml)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"demo {__import__('demo').__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from demo.app import EditorApp
    from demo.config import load_config

    config = load_config(args.config)
    app = EditorApp(files=args.files, config=config)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
