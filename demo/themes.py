"""Theme helpers for the editor widget."""

from __future__ import annotations

AVAILABLE_THEMES = frozenset({"css", "dracula", "github_light", "monokai", "vscode_dark"})
DEFAULT_THEME = "vscode_dark"


def validate_theme(name: str) -> str:
    """Return *name* if it is a known TextArea theme, else the default."""
    return name if name in AVAILABLE_THEMES else DEFAULT_THEME
