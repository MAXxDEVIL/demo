"""CommandPalette: fuzzy command switcher opened with Alt+X."""

from __future__ import annotations

from collections.abc import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input, OptionList

from demo.keymap import format_key
from textual.widgets._option_list import Option


class PaletteInput(Input):
    BINDINGS = [
        Binding("up", "list_previous", "Previous"),
        Binding("down", "list_next", "Next"),
        Binding("escape", "close", "Close"),
    ]

    def _palette(self) -> "CommandPalette":
        return self.parent if isinstance(self.parent, CommandPalette) else self.app.query_one(CommandPalette)  # type: ignore[return-value]

    def action_list_previous(self) -> None:
        self._palette().list_previous()

    def action_list_next(self) -> None:
        self._palette().list_next()

    def action_close(self) -> None:
        self._palette().close()


def fuzzy_score(query: str, text: str) -> int:
    """Subsequence-based score; higher is a better match. ``-1`` if no match."""
    query = query.lower()
    text = text.lower()
    if not query:
        return 0
    pos = 0
    score = 0
    last = -1
    for char in query:
        found = text.find(char, pos)
        if found == -1:
            return -1
        if found == pos:
            score += 3
        elif last != -1 and found == last + 1:
            score += 2
        score += 1
        pos = found + 1
        last = found
    if text.startswith(query):
        score += 10
    return score


class CommandPalette(Vertical):
    """A modal palette of named commands, filtered as you type."""

    BINDINGS: list[Binding] = [Binding("escape", "close", "Close")]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._commands: dict[str, Callable[[], None]] = {}
        self._shortcuts: dict[str, str] = {}
        self._rows: list[tuple[str, str, str]] = []

    def compose(self) -> ComposeResult:
        yield Input(id="palette-input", placeholder="Type a command…")
        yield OptionList(id="palette-list")

    def on_mount(self) -> None:
        self.display = False
        self.border_title = "Command palette"

    def set_commands(self, commands: dict[str, Callable[[], None]], shortcuts: dict[str, str] | None = None) -> None:
        """Register the full command set and rebuild the option list."""
        self._commands = commands
        self._shortcuts = shortcuts or {}
        self._rows = [
            (name, format_key(self._shortcuts[name]) if name in self._shortcuts else "", action)
            for name, action in commands.items()
        ]
        self.refresh_options("")

    def open(self) -> None:
        self.refresh_options("")
        self.display = True
        self.focus()
        self.query_one("#palette-input").focus()

    def close(self) -> None:
        self.display = False
        self.app.focus_editor()  # type: ignore[attr-defined]

    def refresh_options(self, query: str) -> None:
        scored: list[tuple[int, str, str]] = []
        for name, detail, action in self._rows:
            score = fuzzy_score(query, name)
            if score == -1:
                continue
            scored.append((-score, name, detail))
        scored.sort(key=lambda t: (t[0], t[1]))
        options = [Option(prompt=name if not detail else f"{name}  —  {detail}", id=name) for _, name, detail in scored]
        option_list = self.query_one("#palette-list")
        option_list.clear_options()
        option_list.add_options(options)
        if options:
            option_list.highlighted = 0
        self._names = [name for _, name, _ in scored]

    def on_input_changed(self, event: Input.Changed) -> None:
        event.stop()
        self.refresh_options(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.run_highlighted()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        self.run_command(event.option.id)

    def list_previous(self) -> None:
        self.query_one("#palette-list").action_cursor_up()

    def list_next(self) -> None:
        self.query_one("#palette-list").action_cursor_down()

    def run_highlighted(self) -> None:
        option = self.query_one("#palette-list").highlighted_option
        if option is not None:
            self.run_command(option.id)

    def run_command(self, name: str | None) -> None:
        if name is None:
            return
        self.close()
        action = self._commands.get(name)
        if action is not None:
            action()
