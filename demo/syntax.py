"""Language detection by file name / extension.

Textual's `TextArea` supports a fixed set of tree-sitter languages. Anything
outside that set is treated as plain text (language ``None``).
"""

from pathlib import Path

EXTENSION_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".pyw": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".ksh": "bash",
    ".go": "go",
    ".rs": "rust",
    ".json": "json",
    ".jsonc": "json",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".java": "java",
    ".sql": "sql",
    ".xml": "xml",
    ".reg": "regex",
    ".re": "regex",
}

FILENAME_LANGUAGE: dict[str, str] = {
    "makefile": None,
    "dockerfile": None,
    ".gitignore": None,
    ".bashrc": "bash",
    ".bash_profile": "bash",
    ".zshrc": "bash",
}

TEXTUAL_LANGUAGES: set[str] = {
    "bash",
    "css",
    "go",
    "html",
    "java",
    "javascript",
    "json",
    "markdown",
    "python",
    "regex",
    "rust",
    "sql",
    "toml",
    "xml",
    "yaml",
}


def detect_language(path: str | Path | None) -> str | None:
    """Return the Textual language name for *path*, or ``None`` for plain text."""
    if not path:
        return None
    path = Path(path)
    name = path.name.lower()
    if name in FILENAME_LANGUAGE:
        return FILENAME_LANGUAGE[name]
    language = EXTENSION_LANGUAGE.get(path.suffix.lower())
    if language is not None and language not in TEXTUAL_LANGUAGES:
        return None
    return language
