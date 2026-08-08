"""Central keybinding definitions.

This is the single source of truth for the keymap. It is used both to build
``BINDINGS`` lists (in ``CodeEditor`` and ``EditorApp``) and to render the
``F1`` help screen.
"""

from __future__ import annotations

from textual.binding import Binding

# Actions handled by the CodeEditor widget itself.
EDITOR_BINDINGS: list[Binding] = [
    Binding("ctrl+b", "cursor_left", "Character left", show=False),
    Binding("ctrl+p", "cursor_up", "Line up", show=False),
    Binding("ctrl+n", "cursor_down", "Line down", show=False),
    Binding("alt+f", "cursor_word_right", "Word right", show=False),
    Binding("alt+b", "cursor_word_left", "Word left", show=False),
    Binding("ctrl+home", "cursor_top", "Document start", show=False),
    Binding("ctrl+end", "cursor_bottom", "Document end", show=False),
    Binding("alt+d", "delete_word_right", "Delete word right", show=False),
    Binding("ctrl+k", "kill_line", "Kill line", show=False),
    Binding("ctrl+w", "cut_selection", "Cut selection", show=False),
    Binding("ctrl+u", "yank", "Paste (yank)", show=False),
    Binding("alt+t", "transpose_chars", "Transpose characters", show=False),
    Binding("alt+/", "toggle_comment", "Toggle comment", show=False),
    Binding("shift+tab", "unindent_line", "Unindent line", show=False),
    Binding("alt+n", "select_next_occurrence", "Select next occurrence", show=False),
    Binding("alt+up", "move_line_up", "Move line up", show=False),
    Binding("alt+down", "move_line_down", "Move line down", show=False),
    Binding("alt+shift+d", "duplicate_line", "Duplicate line", show=False),
    Binding("ctrl+shift+z", "redo", "Redo", show=False),
]

# Actions forwarded to the app (buffer management, search, navigation).
APP_BINDINGS: list[Binding] = [
    Binding("ctrl+o", "save_file", "Save file"),
    Binding("ctrl+shift+s", "save_file_as", "Save file as"),
    Binding("ctrl+t", "open_file", "Open file"),
    Binding("ctrl+x", "quit", "Quit"),
    Binding("ctrl+q", "quit", "Quit"),
    Binding("ctrl+tab", "next_buffer", "Next buffer"),
    Binding("ctrl+shift+tab", "previous_buffer", "Previous buffer"),
    Binding("ctrl+f", "find", "Find"),
    Binding("ctrl+r", "replace", "Replace"),
    Binding("ctrl+g", "goto_line", "Go to line"),
    Binding("alt+x", "command_palette", "Command palette"),
    Binding("f1", "help", "Help"),
    Binding("alt+h", "hover", "Hover documentation"),
    Binding("alt+.", "definition", "Go to definition"),
    Binding("alt+1", "goto_buffer_1", "Buffer 1", show=False),
    Binding("alt+2", "goto_buffer_2", "Buffer 2", show=False),
    Binding("alt+3", "goto_buffer_3", "Buffer 3", show=False),
    Binding("alt+4", "goto_buffer_4", "Buffer 4", show=False),
    Binding("alt+5", "goto_buffer_5", "Buffer 5", show=False),
    Binding("alt+6", "goto_buffer_6", "Buffer 6", show=False),
    Binding("alt+7", "goto_buffer_7", "Buffer 7", show=False),
    Binding("alt+8", "goto_buffer_8", "Buffer 8", show=False),
    Binding("alt+9", "goto_buffer_9", "Buffer 9", show=False),
]

# Human-readable reference used by the F1 help overlay.
HELP_ROWS: list[tuple[str, str]] = [
    ("File", ""),
    ("Ctrl+O", "Save file"),
    ("Ctrl+Shift+S", "Save file as"),
    ("Ctrl+T", "Open file"),
    ("Ctrl+X / Ctrl+Q", "Quit"),
    ("", ""),
    ("Editing", ""),
    ("Ctrl+K", "Kill line (into kill ring)"),
    ("Ctrl+W", "Cut selection"),
    ("Ctrl+U", "Paste (yank)"),
    ("Ctrl+Z / Ctrl+Shift+Z", "Undo / redo"),
    ("Ctrl+D / Backspace", "Delete right / left"),
    ("Alt+D", "Delete word right"),
    ("Alt+T", "Transpose characters"),
    ("Alt+/", "Toggle line comment"),
    ("Tab / Shift+Tab", "Indent / unindent"),
    ("Alt+N", "Select next occurrence"),
    ("Alt+Up / Alt+Down", "Move line up / down"),
    ("Alt+Shift+D", "Duplicate line"),
    ("", ""),
    ("Movement", ""),
    ("Ctrl+B / Ctrl+F", "Character left / right"),
    ("Ctrl+P / Ctrl+N", "Line up / down"),
    ("Ctrl+A / Ctrl+E", "Line start / end"),
    ("Alt+B / Alt+F", "Word left / right"),
    ("Ctrl+Home / Ctrl+End", "Document start / end"),
    ("PageUp / PageDown", "Page up / down"),
    ("Shift+arrows", "Extend selection"),
    ("", ""),
    ("Buffers", ""),
    ("Ctrl+Tab", "Next buffer"),
    ("Ctrl+Shift+Tab", "Previous buffer"),
    ("Alt+1 ... Alt+9", "Jump to buffer"),
    ("", ""),
    ("Search", ""),
    ("Ctrl+F", "Find (Enter next, Ctrl+P prev, Esc close)"),
    ("Ctrl+R", "Query replace"),
    ("Ctrl+G", "Go to line"),
    ("", ""),
    ("Language server", ""),
    ("Alt+H", "Hover documentation"),
    ("Alt+.", "Go to definition"),
    ("", ""),
    ("App", ""),
    ("Alt+X", "Command palette"),
    ("F1", "This help"),
]
