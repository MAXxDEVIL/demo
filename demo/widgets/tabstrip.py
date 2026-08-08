"""TabStrip: a horizontal bar of buffer tabs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button

if TYPE_CHECKING:
    from demo.buffers import Buffer


class TabStrip(Horizontal):
    """Renders one button per open buffer, highlighting the active one."""

    class TabActivated(Message):
        """Posted when the user clicks a tab button."""

        def __init__(self, index: int) -> None:
            self.index = index
            super().__init__()

    def set_buffers(self, buffers: list["Buffer"], active_index: int) -> None:
        self.remove_children()
        for index, buffer in enumerate(buffers):
            label = f"{buffer.name}{'*' if buffer.is_modified else ''}"
            button = Button(label, classes="tab" + (" active" if index == active_index else ""))
            button.can_focus = False
            button._buffer_index = index  # type: ignore[attr-defined]
            self.mount(button)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        index = getattr(event.button, "_buffer_index", None)
        event.stop()
        if index is not None:
            self.post_message(self.TabActivated(index))
