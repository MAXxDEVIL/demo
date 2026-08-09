"""TabStrip: a horizontal bar of buffer tabs with close buttons."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Static

if TYPE_CHECKING:
    from demo.buffers import Buffer


class Tab(Horizontal):
    """A single buffer tab: a clickable label plus a close button."""

    def __init__(self, index: int, label: str, active: bool) -> None:
        super().__init__()
        self._index = index
        self._label_text = label
        self._active = active

    def compose(self) -> ComposeResult:
        yield Static(
            self._label_text,
            classes="tab" + (" active" if self._active else ""),
            id=f"tab-label-{self._index}",
        )
        yield Button("×", id=f"tab-close-{self._index}", classes="tab-close")

    def on_click(self, event) -> None:
        if not isinstance(event.widget, Button):
            event.stop()
            strip = self.app.query_one(TabStrip)
            strip.post_message(strip.TabActivated(self._index))


class TabStrip(Horizontal):
    """Renders one tab per open buffer, highlighting the active one."""

    class TabActivated(Message):
        """Posted when the user clicks a tab."""

        def __init__(self, index: int) -> None:
            self.index = index
            super().__init__()

    class TabClosed(Message):
        """Posted when the user clicks a tab's close button."""

        def __init__(self, index: int) -> None:
            self.index = index
            super().__init__()

    def set_buffers(self, buffers: list["Buffer"], active_index: int) -> None:
        self.remove_children()
        for index, buffer in enumerate(buffers):
            label = f"{buffer.name}{'*' if buffer.is_modified else ''}"
            tab = Tab(index, label, index == active_index)
            tab.styles.width = "auto"
            self.mount(tab)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        widget_id = event.button.id or ""
        event.stop()
        if widget_id.startswith("tab-close-"):
            index = int(widget_id[len("tab-close-"):])
            self.post_message(self.TabClosed(index))
