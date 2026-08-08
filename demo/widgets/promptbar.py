"""PromptBar: a labelled single-input bar used for opening files, save-as and go-to-line."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Input, Static

MODES = ("open", "save_as", "goto")


class PromptInput(Input):
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("tab", "complete", "Complete"),
    ]

    def _bar(self) -> "PromptBar":
        return self.parent if isinstance(self.parent, PromptBar) else self.app.query_one(PromptBar)  # type: ignore[return-value]

    def action_close(self) -> None:
        self._bar().close()

    def action_complete(self) -> None:
        self._bar().complete()


class PromptBar(Horizontal):
    """A bottom-docked bar with a label and a single-line input."""

    BINDINGS: list[Binding] = [Binding("escape", "close", "Close")]

    def compose(self) -> ComposeResult:
        yield Static("", id="prompt-label")
        yield PromptInput(id="prompt-input", placeholder="")

    def on_mount(self) -> None:
        self.display = False

    def open(self, mode: str, label: str, value: str = "") -> None:
        self._mode = mode
        self.query_one("#prompt-label").update(label)
        prompt = self.query_one("#prompt-input")
        prompt.value = value
        prompt.action_home()
        self.display = True
        prompt.focus()

    def close(self) -> None:
        self.display = False
        self.app.focus_editor()  # type: ignore[attr-defined]

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.submit(event.value.strip())

    def submit(self, value: str) -> None:
        mode = getattr(self, "_mode", "open")
        if mode == "goto":
            self.app.goto_line_number(value)  # type: ignore[attr-defined]
        elif mode == "open":
            self.app.open_path(value)  # type: ignore[attr-defined]
        elif mode == "save_as":
            self.app.save_path(value)  # type: ignore[attr-defined]
        else:
            self.close()

    def complete(self) -> None:
        """Tab-complete a path from the current directory."""
        mode = getattr(self, "_mode", "open")
        if mode not in ("open", "save_as"):
            return
        prompt = self.query_one("#prompt-input")
        raw = prompt.value.strip()
        if not raw:
            return
        path = Path(raw).expanduser()
        directory = path if path.is_dir() else path.parent
        stem = path.name
        if directory.exists():
            matches = [p for p in directory.iterdir() if p.name.startswith(stem)]
            if len(matches) == 1:
                prompt.value = str(matches[0])
                prompt.action_end()
