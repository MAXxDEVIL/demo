"""FindReplaceBar: incremental find and query-replace bar.

Two inputs (find, replace).  The replace input is only shown in replace mode.
Key handling lives on the inputs so it only applies while the bar is focused.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.document._document import Selection
from textual.widgets import Input, Static

from demo import search


class FindInput(Input):
    """Input for the search query."""

    BINDINGS = [
        Binding("enter", "next", "Next match"),
        Binding("ctrl+f", "next", "Next match"),
        Binding("ctrl+p", "previous", "Previous match"),
        Binding("ctrl+r", "to_replace", "Replace mode"),
        Binding("escape", "close", "Close"),
    ]

    def _bar(self) -> "FindReplaceBar":
        return self.parent if isinstance(self.parent, FindReplaceBar) else self.app.query_one(FindReplaceBar)  # type: ignore[return-value]

    def action_next(self) -> None:
        self._bar().find_next()

    def action_previous(self) -> None:
        self._bar().find_previous()

    def action_to_replace(self) -> None:
        self._bar().enter_replace_mode()

    def action_close(self) -> None:
        self._bar().close()


class ReplaceInput(Input):
    """Input for the replacement text."""

    BINDINGS = [
        Binding("enter", "replace_next", "Replace and find next"),
        Binding("ctrl+p", "previous", "Previous match"),
        Binding("ctrl+t", "to_find", "Find mode"),
        Binding("alt+a", "replace_all", "Replace all"),
        Binding("escape", "close", "Close"),
    ]

    def _bar(self) -> "FindReplaceBar":
        return self.parent if isinstance(self.parent, FindReplaceBar) else self.app.query_one(FindReplaceBar)  # type: ignore[return-value]

    def action_replace_next(self) -> None:
        self._bar().replace_next()

    def action_previous(self) -> None:
        self._bar().find_previous()

    def action_to_find(self) -> None:
        self._bar().enter_find_mode()

    def action_replace_all(self) -> None:
        self._bar().replace_all()

    def action_close(self) -> None:
        self._bar().close()


class FindReplaceBar(Horizontal):
    """The find / replace widget docked at the bottom of the editor."""

    BINDINGS: list[Binding] = [Binding("escape", "close", "Close")]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._mode: str = "find"
        self._query = ""
        self._case_sensitive = False
        self._last_match: tuple[int, int] | None = None
        self._total = 0

    def compose(self) -> ComposeResult:
        yield Static("Find:", id="find-label")
        yield FindInput(id="find-input", placeholder="search")
        yield Static("", id="find-status")
        yield Static("Replace:", id="replace-label")
        yield ReplaceInput(id="replace-input", placeholder="replace")

    def on_mount(self) -> None:
        self.query_one("#replace-label").display = False
        self.query_one("#replace-input").display = False
        self._mode = "find"

    def open(self, mode: str, query: str = "") -> None:
        """Show the bar in *mode* ('find' or 'replace') with an initial query."""
        self._mode = mode
        self._case_sensitive = self.app.config.case_sensitive_search if hasattr(self.app, "config") else False
        self.query_one("#find-input").value = query or ""
        self.query_one("#find-input").action_home()
        self.query_one("#find-status").update("")
        replace_label = self.query_one("#replace-label")
        replace_input = self.query_one("#replace-input")
        replace_label.display = mode == "replace"
        replace_input.display = mode == "replace"
        self.display = True
        if mode == "replace":
            replace_input.focus()
        else:
            self.query_one("#find-input").focus()

    def close(self) -> None:
        self.display = False
        self.app.focus_editor()

    def _editor(self):
        return self.app.current_editor  # type: ignore[attr-defined]

    def _update_query(self) -> str:
        self._query = self.query_one("#find-input").value
        return self._query

    def find_next(self) -> None:
        query = self._update_query()
        editor = self._editor()
        if not query or editor is None:
            self.query_one("#find-status").update("")
            return
        from_index = self._cursor_index(editor) + (0 if self._last_match is None else 1)
        match = self._find(editor, query, from_index, direction=1)
        self._apply_match(editor, match)

    def find_previous(self) -> None:
        query = self._update_query()
        editor = self._editor()
        if not query or editor is None:
            return
        from_index = self._cursor_index(editor)
        match = self._find(editor, query, from_index, direction=-1)
        self._apply_match(editor, match)

    def _find(self, editor, query, from_index, direction):
        match = search.next_match(editor.text, query, from_index, direction=direction, case_sensitive=self._case_sensitive)
        self._total = len(search.find_all(editor.text, query, case_sensitive=self._case_sensitive))
        return match

    def _cursor_index(self, editor) -> int:
        return search.location_to_index(editor.text, editor.selection.end)

    def _apply_match(self, editor, match) -> None:
        self._last_match = match
        status = self.query_one("#find-status")
        if match is None:
            status.update(f"no matches")
            return
        start, end = match
        editor.selection = Selection(
            search.index_to_location(editor.text, start),
            search.index_to_location(editor.text, end),
        )
        editor.scroll_cursor_visible()
        order = 1
        for s, e in search.find_all(editor.text, self._query, case_sensitive=self._case_sensitive):
            if (s, e) == match:
                break
            order += 1
        status.update(f"{order}/{self._total}")

    def replace_next(self) -> None:
        editor = self._editor()
        if editor is None:
            return
        query = self._update_query()
        if not query:
            return
        replacement = self.query_one("#replace-input").value
        self._case_sensitive = self.app.config.case_sensitive_search if hasattr(self.app, "config") else False
        text = editor.text
        from_index = self._cursor_index(editor) + (0 if self._last_match is None else 1)
        match = search.next_match(text, query, from_index, direction=1, case_sensitive=self._case_sensitive)
        if match is None:
            self.query_one("#find-status").update("no matches")
            return
        start, end = match
        editor.replace(
            replacement,
            search.index_to_location(text, start),
            search.index_to_location(text, end),
        )
        self._last_match = None
        editor.move_cursor(search.index_to_location(text, start))
        editor.scroll_cursor_visible()
        self.find_next()

    def replace_all(self) -> None:
        editor = self._editor()
        if editor is None:
            return
        query = self._update_query()
        if not query:
            return
        replacement = self.query_one("#replace-input").value
        self._case_sensitive = self.app.config.case_sensitive_search if hasattr(self.app, "config") else False
        matches = search.find_all(editor.text, query, case_sensitive=self._case_sensitive)
        for start, end in reversed(matches):
            editor.replace(
                replacement,
                search.index_to_location(editor.text, start),
                search.index_to_location(editor.text, end),
            )
        self.query_one("#find-status").update(f"replaced {len(matches)}")
        self._last_match = None

    def enter_replace_mode(self) -> None:
        self._mode = "replace"
        self.query_one("#replace-label").display = True
        self.query_one("#replace-input").display = True
        self.query_one("#replace-input").focus()

    def enter_find_mode(self) -> None:
        self._mode = "find"
        self.query_one("#replace-label").display = False
        self.query_one("#replace-input").display = False
        self.query_one("#find-input").focus()
