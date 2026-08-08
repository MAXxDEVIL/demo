"""Configuration loading for demo.

Configuration lives in ``~/.config/demo/config.toml``. Only the keys present
in the file override the built-in defaults.
"""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "demo" / "config.toml"


@dataclass
class Config:
    theme: str = "vscode_dark"
    soft_wrap: bool = False
    show_line_numbers: bool = True
    indent_width: int = 4
    tab_behavior: str = "indent"
    highlight_cursor_line: bool = True
    case_sensitive_search: bool = False
    plugins_dir: str = str(Path.home() / ".config" / "demo" / "plugins")
    lsp: dict[str, list[str]] = field(default_factory=dict)


def load_config(path: str | Path | None = None) -> Config:
    """Load configuration from *path* (default: ``~/.config/demo/config.toml``)."""
    config = Config()
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not path.exists():
        return config
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"demo: could not read config {path}: {exc}", file=sys.stderr)
        return config

    valid = {f.name for f in fields(config)}
    for key, value in data.items():
        if key not in valid:
            print(f"demo: ignoring unknown config key '{key}'", file=sys.stderr)
            continue
        setattr(config, key, value)
    return config


def plugins_directory(config: Config) -> Path:
    """Resolve (and create) the plugin directory for *config*."""
    path = Path(os.path.expanduser(config.plugins_dir))
    path.mkdir(parents=True, exist_ok=True)
    return path
