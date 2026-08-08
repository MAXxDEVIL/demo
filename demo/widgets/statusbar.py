"""StatusBar: shows buffer name, cursor position, language, git and LSP info."""

from __future__ import annotations

from textual.widgets import Static
from rich.text import Text


class StatusBar(Static):
    """A single-line status area rendered with Rich ``Text``."""

    def set_status(
        self,
        *,
        name: str,
        modified: bool,
        row: int,
        col: int,
        language: str | None,
        branch: str | None = None,
        dirty: bool = False,
        diagnostics: int = 0,
    ) -> None:
        parts: list[object] = []
        parts.append(Text(f"{'*' if modified else ' '} {name}", style="bold"))
        parts.append(Text(f"  {row}:{col}", style="dim"))
        parts.append(Text(f"  [{language or 'text'}]", style="italic"))
        if branch:
            parts.append(Text(f"  git: {branch}", style="cyan"))
            parts.append(Text(" *" if dirty else "", style="yellow bold"))
        if diagnostics:
            parts.append(Text(f"  LSP: {diagnostics} problem{'s' if diagnostics != 1 else ''}", style="red bold"))
        self.update(Text.assemble(*parts))
