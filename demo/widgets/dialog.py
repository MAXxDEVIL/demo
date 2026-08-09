"""Dialog: a small modal confirm widget for close-buffer and quit flows."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Static


class Dialog(Vertical):
    """A modal prompt with a message and a row of labelled buttons.

    The host app opens it with :meth:`show` and receives the chosen action
    back through the :class:`Dialog.Answered` message. ``Escape`` answers
    with ``"cancel"``.
    """

    class Answered(Message):
        """Posted when a button is pressed or ``Escape`` is used."""

        def __init__(self, action: str) -> None:
            self.action = action
            super().__init__()

    BINDINGS: list[Binding] = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, *, title: str = "", id: str | None = None) -> None:
        super().__init__(id=id)
        self._title = title

    def compose(self) -> ComposeResult:
        yield Static(self._title, id="dialog-title")
        yield Static("", id="dialog-message")
        yield Horizontal(id="dialog-buttons")

    def on_mount(self) -> None:
        self.display = False

    def show(self, title: str, message: str, actions: list[tuple[str, str]]) -> None:
        """Show *message* with one button per ``(label, action)`` pair."""
        self.query_one("#dialog-title").update(title)
        self.query_one("#dialog-message").update(message)
        buttons = self.query_one("#dialog-buttons")
        buttons.remove_children()
        for label, action in actions:
            buttons.mount(Button(label, id=f"dialog-{action}"))
        self.display = True
        self.focus()
        cancel = self.query_one("#dialog-cancel")
        (cancel or self).focus()

    def action_cancel(self) -> None:
        self._finish("cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        widget_id = event.button.id or ""
        if widget_id.startswith("dialog-"):
            self._finish(widget_id[len("dialog-"):])

    def _finish(self, action: str) -> None:
        self.display = False
        self.post_message(self.Answered(action))
        self.app.focus_editor()
