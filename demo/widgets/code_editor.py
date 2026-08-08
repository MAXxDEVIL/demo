"""CodeEditor: the editing widget, a ``TextArea`` subclass.

Adds Emacs-style kill-ring editing (kill line, cut, yank) plus a few
text-editing conveniences (transpose, comment toggle, unindent) on top of the
built-in movement, selection, undo/redo and syntax highlighting.  Keys that
belong to the application (save, open, search, tabs, ...) are forwarded to the
host app.
"""

from __future__ import annotations

from typing import ClassVar

from textual.binding import Binding
from textual.document._document import Selection
from textual.widgets import TextArea

from demo.keymap import APP_BINDINGS, EDITOR_BINDINGS
from demo.search import index_to_location, location_to_index

COMMENT_PREFIX: dict[str, str | None] = {
    "python": "#",
    "bash": "#",
    "toml": "#",
    "yaml": "#",
    "sql": "--",
    "go": "//",
    "rust": "//",
    "javascript": "//",
    "java": "//",
    "css": "/*",
    "html": "<!--",
    "xml": "<!--",
}


class CodeEditor(TextArea):
    """A text editor widget with a shared kill ring and app-level keys."""

    BINDINGS: list[Binding] = [
        *EDITOR_BINDINGS,
        *APP_BINDINGS,
        Binding("escape", "noop", show=False),
    ]

    kill_ring: ClassVar[list[str]] = []

    def _forward(self, action: str, *args: object) -> None:
        """Run *action* on the host app if one is available."""
        app = getattr(self, "app", None)
        if app is not None and hasattr(app, f"action_{action}"):
            getattr(app, f"action_{action}")(*args)

    def _selected_range(self) -> tuple[tuple[int, int], tuple[int, int]]:
        """Return the ``(start, end)`` locations of the current selection."""
        selection = self.selection
        return (selection.start, selection.end)

    def action_noop(self) -> None:
        """Consume the key and do nothing (e.g. Escape in the editor)."""

    def action_kill_line(self) -> None:
        """Kill the rest of the line (or the selection) into the kill ring."""
        start, end = self._selected_range()
        if start != end:
            killed = self.selected_text
            self.replace("", start, end)
            if killed:
                self._kill(killed)
            return
        text = self.text
        index = location_to_index(text, start)
        end_index = text.find("\n", index)
        if end_index == -1:
            end_index = len(text)
        chunk = text[index:end_index]
        if chunk:
            self._kill(chunk)
            if end_index < len(text) and text[end_index] == "\n":
                end_index += 1
            self.delete(index_to_location(text, index), index_to_location(text, end_index))
        elif end_index < len(text):
            chunk = "\n"
            self._kill(chunk)
            self.delete(start, index_to_location(text, end_index + 1))

    def action_cut_selection(self) -> None:
        """Cut the selection into the kill ring; cut the whole line if none."""
        start, end = self._selected_range()
        if start == end:
            self._kill_line_whole()
        else:
            self.action_kill_line()

    def _kill_line_whole(self) -> None:
        """Cut the current line (including its newline) into the kill ring."""
        text = self.text
        lines = text.split("\n")
        row = self.selection.end[0]
        line = lines[row]
        self._kill(line + "\n")
        if len(lines) == 1:
            self.delete((row, 0), (row, len(line)))
        elif row == len(lines) - 1:
            self.delete((row - 1, len(lines[row - 1])), (row, len(line)))
        else:
            self.delete((row, 0), (row + 1, 0))

    def action_yank(self) -> None:
        """Insert the most recent killed text at the cursor."""
        if not self.kill_ring:
            return
        self.insert(self.kill_ring[-1])

    def _kill(self, text: str) -> None:
        self.kill_ring.append(text)

    def action_transpose_chars(self) -> None:
        """Swap the two characters around the cursor (Emacs ``C-t``)."""
        text = self.text
        start, _ = self._selected_range()
        index = location_to_index(text, start)
        if index == 0:
            return
        left = index - 1
        right = index
        if right >= len(text) or text[left] == "\n" or text[right] == "\n":
            left = index - 2
            right = index - 1
            if left < 0:
                return
            if text[left] == "\n" or text[right] == "\n":
                return
        swapped = text[right] + text[left]
        self.replace(swapped, index_to_location(text, left), index_to_location(text, right + 1))

    def action_toggle_comment(self) -> None:
        """Comment or uncomment the lines overlapping the selection."""
        prefix = COMMENT_PREFIX.get(self.language or "", None)
        if prefix is None:
            self.notify("No comment syntax for this language", severity="warning")
            return
        start, end = self._selected_range()
        text = self.text
        lines = text.split("\n")
        start_row = start[0]
        end_row = end[0] if end[1] or end[0] > start[0] else start[0]
        if start == end:
            end_row = start_row
        new_lines = []
        for row in range(start_row, end_row + 1):
            line = lines[row]
            stripped = line.lstrip()
            indent = line[: len(line) - len(stripped)]
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix) :]
                if stripped.startswith(" "):
                    stripped = stripped[1:]
            else:
                stripped = f"{prefix} {stripped}"
            new_lines.append(indent + stripped)
        replaced = "\n".join(new_lines)
        start_loc = (start_row, 0)
        end_loc = (end_row, len(lines[end_row]))
        self.replace(replaced, start_loc, end_loc)
        column = min(start[1], len(new_lines[start_row - start_row]))
        self.move_cursor((start_row, column))

    def action_unindent_line(self) -> None:
        """Remove one level of indentation from the lines under the selection."""
        start, end = self._selected_range()
        text = self.text
        lines = text.split("\n")
        start_row = start[0]
        end_row = end[0] if end[0] > start[0] else start[0]
        width = self.indent_width
        new_lines = []
        for row in range(start_row, end_row + 1):
            line = lines[row]
            if line.startswith("\t"):
                new_lines.append(line[1:])
            else:
                spaces = len(line) - len(line.lstrip(" "))
                remove = min(spaces, width)
                new_lines.append(line[remove:])
        replaced = "\n".join(new_lines)
        start_loc = (start_row, 0)
        end_loc = (end_row, len(lines[end_row]))
        self.replace(replaced, start_loc, end_loc)
        self.move_cursor((start_row, start[1] - min(start[1], width) if start == end else start[1]))

    def action_cursor_top(self) -> None:
        self.move_cursor((0, 0))

    def action_cursor_bottom(self) -> None:
        row = max(0, len(self.text.split("\n")) - 1)
        self.move_cursor((row, 0))

    def _word_at_cursor(self) -> str:
        text = self.text
        from demo import search

        index = search.location_to_index(text, self.selection.end)

        def is_word_char(char: str) -> bool:
            return char.isalnum() or char == "_"

        left = index
        while left > 0 and is_word_char(text[left - 1]):
            left -= 1
        right = index
        while right < len(text) and is_word_char(text[right]):
            right += 1
        return text[left:right]

    def action_select_next_occurrence(self) -> None:
        """Select the next occurrence of the current selection (or word)."""
        from demo import search

        text = self.text
        if self.selection.is_empty:
            query = self._word_at_cursor()
            if not query:
                return
            index = search.location_to_index(text, self.selection.end)
            matches = search.find_all(text, query, case_sensitive=True)
            match = next((m for m in matches if m[0] <= index < m[1]), None)
            if match is None:
                match = next((m for m in matches if m[0] >= index), None)
        else:
            query = self.selected_text
            if not query:
                return
            from_index = search.location_to_index(text, self.selection.end)
            match = search.next_match(text, query, from_index + 1, case_sensitive=True)
        if match is None:
            return
        start, end = match
        self.selection = Selection(start=search.index_to_location(text, start), end=search.index_to_location(text, end))
        self.scroll_cursor_visible()

    def action_move_line_down(self) -> None:
        self._move_lines(1)

    def action_move_line_up(self) -> None:
        self._move_lines(-1)

    def _move_lines(self, direction: int) -> None:
        start, end = self.selection
        orig = self.text.split("\n")
        top = start[0]
        bottom = end[0]
        if start == end:
            bottom = top
        elif end[1] == 0 and bottom > top:
            bottom -= 1
        new = list(orig)
        if direction > 0:
            if bottom + 1 >= len(orig):
                return
            new[top : bottom + 2] = [orig[bottom + 1]] + orig[top : bottom + 1]
            region_start, region_end = top, bottom + 1
            new_row = top + 1
        else:
            if top - 1 < 0:
                return
            new[top - 1 : bottom + 1] = orig[top : bottom + 1] + [orig[top - 1]]
            region_start, region_end = top - 1, bottom
            new_row = top - 1
        region_text = "\n".join(new[region_start : region_end + 1])
        start_loc = (region_start, 0)
        end_loc = (region_end, len(orig[region_end]))
        self.replace(region_text, start_loc, end_loc)
        self.move_cursor((new_row, start[1]))

    def action_duplicate_line(self) -> None:
        lines = self.text.split("\n")
        row = self.selection.end[0]
        line = lines[row]
        if row == len(lines) - 1:
            insert_text = f"{line}\n{line}"
            end_loc = (row, len(line))
        else:
            insert_text = f"{line}\n{line}\n"
            end_loc = (row + 1, 0)
        self.replace(insert_text, (row, 0), end_loc)
        self.move_cursor((row + 1, self.selection.end[1]))

    # --- App forwarding -------------------------------------------------
    def action_save_file(self) -> None:
        self._forward("save_file")

    def action_save_file_as(self) -> None:
        self._forward("save_file_as")

    def action_open_file(self) -> None:
        self._forward("open_file")

    def action_quit(self) -> None:
        self._forward("quit")

    def action_next_buffer(self) -> None:
        self._forward("next_buffer")

    def action_previous_buffer(self) -> None:
        self._forward("previous_buffer")

    def action_find(self) -> None:
        self._forward("find")

    def action_replace(self) -> None:
        self._forward("replace")

    def action_goto_line(self) -> None:
        self._forward("goto_line")

    def action_command_palette(self) -> None:
        self._forward("command_palette")

    def action_help(self) -> None:
        self._forward("help")

    def action_goto_buffer_1(self) -> None:
        self._forward("goto_buffer", 1)

    def action_goto_buffer_2(self) -> None:
        self._forward("goto_buffer", 2)

    def action_goto_buffer_3(self) -> None:
        self._forward("goto_buffer", 3)

    def action_goto_buffer_4(self) -> None:
        self._forward("goto_buffer", 4)

    def action_goto_buffer_5(self) -> None:
        self._forward("goto_buffer", 5)

    def action_goto_buffer_6(self) -> None:
        self._forward("goto_buffer", 6)

    def action_goto_buffer_7(self) -> None:
        self._forward("goto_buffer", 7)

    def action_goto_buffer_8(self) -> None:
        self._forward("goto_buffer", 8)

    def action_goto_buffer_9(self) -> None:
        self._forward("goto_buffer", 9)
