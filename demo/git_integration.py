"""Minimal git integration for the status bar.

Uses the ``git`` executable directly (no third-party dependency).  All calls
are short and time-boxed; failures degrade to ``None``/``False``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(directory: Path, *args: str, timeout: float = 1.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(directory), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _git_root(path: Path) -> Path | None:
    directory = path if path.is_dir() else path.parent
    result = _run_git(directory, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def branch(path: Path | None) -> str | None:
    """Return the current branch name, or ``None`` if not in a repo."""
    if path is None:
        return None
    directory = path if path.is_dir() else path.parent
    result = _run_git(directory, "rev-parse", "--abbrev-ref", "HEAD")
    if result.returncode != 0:
        return None
    name = result.stdout.strip()
    return name or None


def is_dirty(path: Path | None) -> bool:
    """Return ``True`` if *path* has uncommitted changes in its repo."""
    if path is None:
        return False
    root = _git_root(path)
    if root is None:
        return False
    result = _run_git(root, "status", "--porcelain", "--", str(path))
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def status(path: Path | None) -> tuple[str | None, bool]:
    """Return ``(branch, dirty)`` for *path*."""
    return branch(path), is_dirty(path)
