"""HelpView: full-screen keybinding reference overlay (F1)."""

from __future__ import annotations

from rich.table import Table
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from demo.keymap import HELP_ROWS


class HelpView(Static):
    """Renders the keymap reference as a table; Escape closes it."""

    BINDINGS: list[Binding] = [Binding("escape", "close", "Close")]

    def compose(self) -> ComposeResult:
        yield Static("", id="help-body")

    def on_mount(self) -> None:
        self.can_focus = True
        self.border_title = "Keybindings"
        table = Table(show_header=False, expand=True, pad_edge=False)
        table.add_column("Key", style="bold cyan", no_wrap=True)
        table.add_column("Action", no_wrap=False)
        for key, description in HELP_ROWS:
            if key:
                table.add_row(key, description)
            elif description:
                table.add_section()
        self.query_one("#help-body").update(table)

    def show(self) -> None:
        self.display = True
        self.focus()

    def action_close(self) -> None:
        self.display = False
        self.app.focus_editor()  # type: ignore[attr-defined]
