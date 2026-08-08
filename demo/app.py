"""EditorApp: the main application, wiring buffers, widgets and actions together."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header

from demo.buffers import Buffer
from demo.config import Config, load_config
from demo import git_integration
from demo.keymap import APP_BINDINGS
from demo.lsp import LanguageServer, uri_to_path
from demo.plugins import PluginManager
from demo.syntax import detect_language
from demo.themes import validate_theme
from demo.widgets.code_editor import CodeEditor
from demo.widgets.commandpalette import CommandPalette
from demo.widgets.findbar import FindReplaceBar
from demo.widgets.helpview import HelpView
from demo.widgets.promptbar import PromptBar
from demo.widgets.statusbar import StatusBar
from demo.widgets.tabstrip import TabStrip


class EditorApp(App[None]):
    """A modeless, multi-buffer code editor."""

    TITLE = "demo"
    SUB_TITLE = "a modeless CLI code editor"
    BINDINGS = APP_BINDINGS

    CSS = """
    #tabs {
        dock: top;
        height: 1;
        padding: 0 1;
        background: $panel;
    }
    #tabs Button {
        height: 1;
        min-width: 6;
        padding: 0 1 0 1;
        border: none;
        background: $panel;
        color: $text;
    }
    #tabs Button:hover {
        background: $panel-lighten-2;
    }
    #tabs Button.active {
        background: $accent;
        color: $text-accent;
    }
    #content {
        layout: horizontal;
        height: 1fr;
    }
    #content TextArea {
        width: 1fr;
        height: 1fr;
    }
    #statusbar {
        dock: bottom;
        height: 1;
        background: $panel;
        padding: 0 1;
    }
    #findbar {
        dock: bottom;
        height: 1;
        background: $panel-lighten-1;
        padding: 0 1;
    }
    #findbar #find-label, #findbar #replace-label {
        width: auto;
        content-align: right middle;
    }
    #findbar #find-status {
        width: auto;
        content-align: center middle;
        color: $text-muted;
    }
    #findbar Input {
        width: 1fr;
    }
    #promptbar {
        dock: bottom;
        height: 1;
        background: $panel-lighten-1;
        padding: 0 1;
    }
    #promptbar #prompt-label {
        width: auto;
        content-align: right middle;
    }
    #promptbar Input {
        width: 1fr;
    }
    #palette {
        layer: modal;
        align: center top;
        width: 62%;
        height: 14;
        margin-top: 1;
        border: thick $accent;
        background: $surface;
    }
    #palette Input {
        width: 1fr;
        margin: 0 1;
    }
    #palette OptionList {
        height: 1fr;
    }
    #help {
        layer: modal;
        align: center middle;
        width: 90%;
        max-height: 26;
        border: thick $primary;
        background: $surface;
    }
    #help Static {
        padding: 1 2;
    }
    """

    def __init__(self, files: list[str] | None = None, config: Config | None = None) -> None:
        super().__init__()
        self.config = config or load_config()
        self.startup_files = list(files or [])
        self.buffers: list[Buffer] = []
        self.active_index = 0
        self._quit_armed = False
        self._diagnostics: dict[str, int] = {}
        self._git_branch: dict[str, str | None] = {}
        self._git_dirty: dict[str, bool] = {}
        self.plugin_commands: dict[str, object] = {}
        self.plugins = PluginManager(self)
        self._servers: dict[str, LanguageServer] = {}
        self._lsp_starting: set[str] = set()

    # ------------------------------------------------------------------ setup
    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield TabStrip(id="tabs")
        yield Horizontal(id="content")
        yield Footer()
        yield StatusBar(id="statusbar")
        yield FindReplaceBar(id="findbar")
        yield PromptBar(id="promptbar")
        yield CommandPalette(id="palette")
        yield HelpView(id="help")

    def on_mount(self) -> None:
        for widget_id in ("findbar", "promptbar", "palette", "help"):
            self.query_one(f"#{widget_id}").display = False
        self.plugins.load_directory(self.config.plugins_dir)
        for path in self.startup_files:
            self._open_buffer(Path(path))
        if not self.buffers:
            self._open_buffer(None)
        self.set_active(0)
        self.set_interval(5, self._periodic_refresh)

    def _periodic_refresh(self) -> None:
        self._refresh_git()
        buffer = self.active_buffer
        if buffer is not None and buffer.reload_if_clean():
            self.notify(f"Reloaded {buffer.name} from disk")
            self._refresh_tabs()

    # ----------------------------------------------------------------- buffers
    def _new_editor(self, path: Path | None) -> CodeEditor:
        theme = validate_theme(self.config.theme)
        editor = CodeEditor(
            language=detect_language(path),
            theme=theme,
            soft_wrap=self.config.soft_wrap,
            show_line_numbers=self.config.show_line_numbers,
            tab_behavior=self.config.tab_behavior,
            highlight_cursor_line=self.config.highlight_cursor_line,
        )
        editor.indent_width = self.config.indent_width
        return editor

    def _open_buffer(self, path: Path | None) -> Buffer:
        editor = self._new_editor(path)
        buffer = Buffer(path, editor)
        buffer.load()
        self.query_one("#content").mount(editor)
        editor.display = False
        self.buffers.append(buffer)
        self.plugins.run_hook("load", buffer)
        return buffer

    @property
    def active_buffer(self) -> Buffer | None:
        if not self.buffers:
            return None
        return self.buffers[self.active_index % len(self.buffers)]

    @property
    def current_editor(self) -> CodeEditor | None:
        buffer = self.active_buffer
        return buffer.editor if buffer is not None else None

    def set_active(self, index: int) -> None:
        if not self.buffers:
            return
        index %= len(self.buffers)
        self.active_index = index
        for i, buffer in enumerate(self.buffers):
            buffer.editor.display = i == index
        self.query_one("#tabs").set_buffers(self.buffers, index)
        buffer = self.buffers[index]
        if buffer.reload_if_clean():
            self.notify(f"Reloaded {buffer.name} from disk")
            self._refresh_tabs()
        buffer.editor.focus()
        self._ensure_lsp(buffer)
        self.refresh_status()

    def focus_editor(self) -> None:
        editor = self.current_editor
        if editor is not None:
            editor.focus()

    # ------------------------------------------------------------------ status
    def refresh_status(self) -> None:
        buffer = self.active_buffer
        if buffer is None:
            return
        row, col = buffer.editor.selection.end
        key = self._buffer_key(buffer)
        branch = self._git_branch.get(key)
        dirty = self._git_dirty.get(key, False)
        uri = self._uri_for(buffer)
        diagnostics = self._diagnostics.get(uri, 0) if uri else 0
        self.query_one("#statusbar").set_status(
            name=buffer.name,
            modified=buffer.is_modified,
            row=row + 1,
            col=col + 1,
            language=buffer.language,
            branch=branch,
            dirty=dirty,
            diagnostics=diagnostics,
        )

    def _buffer_key(self, buffer: Buffer) -> str:
        return str(buffer.path) if buffer.path is not None else id(buffer)

    # --------------------------------------------------------------------- lsp
    def _uri_for(self, buffer: Buffer) -> str | None:
        if buffer.path is None:
            return None
        return buffer.path.resolve().as_uri()

    def _ensure_lsp(self, buffer: Buffer) -> None:
        language = buffer.language
        if not language or language not in self.config.lsp:
            return
        if language in self._servers or language in self._lsp_starting:
            return
        self._lsp_starting.add(language)
        self.run_worker(
            self._start_lsp_worker(language, self.config.lsp[language]),
            group="lsp",
            name=f"lsp-{language}",
        )

    async def _start_lsp_worker(self, language: str, command: list[str]) -> None:
        server = LanguageServer(self, command, language)
        ok = await server.start()
        self._lsp_starting.discard(language)
        if not ok:
            self.notify(f"Could not start language server for {language}", severity="warning")
            return
        self._servers[language] = server
        for buffer in self.buffers:
            if buffer.language == language and buffer.path is not None:
                uri = self._uri_for(buffer)
                if uri is not None:
                    server.did_open(uri, language, buffer.editor.text)

    def _lsp_for_active(self) -> tuple[LanguageServer | None, str | None]:
        buffer = self.active_buffer
        if buffer is None or buffer.path is None:
            return None, None
        server = self._servers.get(buffer.language or "")
        if server is None:
            return None, None
        return server, self._uri_for(buffer)

    def on_diagnostics_update(self, uri: str) -> None:
        server = next((s for s in self._servers.values() if uri in s.diagnostics), None)
        if server is not None:
            errors = sum(1 for d in server.diagnostics[uri] if (d.severity or 0) <= 2)
            self._diagnostics[uri] = errors
        else:
            self._diagnostics.pop(uri, None)
        self.refresh_status()

    def action_hover(self) -> None:
        server, uri = self._lsp_for_active()
        editor = self.current_editor
        if server is None or uri is None or editor is None:
            self.notify("No language server for this file", severity="warning")
            return
        position = editor.selection.end
        self.run_worker(self._hover_worker(server, uri, position), group="lsp")

    async def _hover_worker(self, server: LanguageServer, uri: str, position) -> None:
        try:
            content = await server.hover(uri, position)
        except (TimeoutError, OSError) as exc:
            self.notify(f"hover failed: {exc}", severity="error")
            return
        if content:
            self.notify(content if len(content) <= 500 else content[:500] + "…")

    def action_definition(self) -> None:
        server, uri = self._lsp_for_active()
        editor = self.current_editor
        if server is None or uri is None or editor is None:
            self.notify("No language server for this file", severity="warning")
            return
        position = editor.selection.end
        self.run_worker(self._definition_worker(server, uri, position), group="lsp")

    async def _definition_worker(self, server: LanguageServer, uri: str, position) -> None:
        try:
            target = await server.definition(uri, position)
        except (TimeoutError, OSError) as exc:
            self.notify(f"go-to-definition failed: {exc}", severity="error")
            return
        if target is None:
            self.notify("No definition found", severity="warning")
            return
        target_uri, line, column = target
        path = uri_to_path(target_uri)
        self.open_path(str(path))
        editor = self.current_editor
        if editor is not None:
            last_row = max(0, len(editor.text.split("\n")) - 1)
            editor.move_cursor((min(line, last_row), column))
            editor.scroll_cursor_visible()

    def _refresh_tabs(self) -> None:
        self.query_one("#tabs").set_buffers(self.buffers, self.active_index)

    def _refresh_git(self) -> None:
        for buffer in self.buffers:
            if buffer.path is None:
                continue
            key = self._buffer_key(buffer)
            self._git_branch[key], self._git_dirty[key] = git_integration.status(buffer.path)
        self.refresh_status()

    # ------------------------------------------------------------------- events
    def _buffer_for_editor(self, editor) -> Buffer | None:
        return next((b for b in self.buffers if b.editor is editor), None)

    def on_text_area_changed(self, event) -> None:
        self._refresh_tabs()
        self.refresh_status()
        buffer = self._buffer_for_editor(event.control)
        if buffer is not None and buffer.path is not None:
            server = self._servers.get(buffer.language or "")
            uri = self._uri_for(buffer)
            if server is not None and uri is not None:
                server.did_change(uri, buffer.editor.text)

    def on_text_area_selection_changed(self, event) -> None:
        self.refresh_status()

    def on_tab_strip_tab_activated(self, event: TabStrip.TabActivated) -> None:
        self.set_active(event.index)

    # ------------------------------------------------------------------- actions
    def action_new_buffer(self) -> None:
        self._open_buffer(None)
        self.set_active(len(self.buffers) - 1)

    def action_save_file(self) -> None:
        buffer = self.active_buffer
        if buffer is None:
            return
        if buffer.path is None:
            self.action_save_file_as()
            return
        try:
            buffer.save()
        except OSError as exc:
            self.notify(f"Could not save {buffer.name}: {exc}", severity="error")
            return
        self.notify(f"Saved {buffer.name}")
        self.plugins.run_hook("save", buffer)
        self._notify_lsp_save(buffer)
        self._refresh_tabs()
        self._refresh_git()

    def _notify_lsp_save(self, buffer: Buffer) -> None:
        server = self._servers.get(buffer.language or "")
        uri = self._uri_for(buffer)
        if server is not None and uri is not None:
            server.did_save(uri)

    def action_save_file_as(self) -> None:
        buffer = self.active_buffer
        value = str(buffer.path) if buffer and buffer.path else ""
        self.query_one("#promptbar").open("save_as", "Save as: ", value)

    def action_open_file(self) -> None:
        buffer = self.active_buffer
        value = str(buffer.path) if buffer and buffer.path else ""
        self.query_one("#promptbar").open("open", "Open: ", value)

    def action_goto_line(self) -> None:
        buffer = self.active_buffer
        value = str(buffer.editor.selection.end[0] + 1) if buffer else ""
        self.query_one("#promptbar").open("goto", "Go to line: ", value)

    def action_next_buffer(self) -> None:
        if self.buffers:
            self.set_active(self.active_index + 1)

    def action_previous_buffer(self) -> None:
        if self.buffers:
            self.set_active(self.active_index - 1)

    def action_goto_buffer(self, number: int) -> None:
        if self.buffers and 1 <= number <= len(self.buffers):
            self.set_active(number - 1)

    def action_find(self) -> None:
        editor = self.current_editor
        query = ""
        if editor is not None:
            query = editor.selected_text or self._word_at_cursor(editor)
        self.query_one("#findbar").open("find", query)

    def action_replace(self) -> None:
        editor = self.current_editor
        query = editor.selected_text if editor else ""
        self.query_one("#findbar").open("replace", query)

    def action_command_palette(self) -> None:
        self.query_one("#palette").set_commands(self.commands())
        self.query_one("#palette").open()

    def action_help(self) -> None:
        self.query_one("#help").show()

    def action_quit(self) -> None:
        if any(buffer.is_modified for buffer in self.buffers):
            if not self._quit_armed:
                self._quit_armed = True
                self.notify("Unsaved changes — press Ctrl+X again to quit without saving", severity="warning")
                self.set_timer(3, self._disarm_quit)
                return
        for server in self._servers.values():
            server.kill()
        self.exit()

    def _disarm_quit(self) -> None:
        self._quit_armed = False

    # ------------------------------------------------------------- palette
    def commands(self) -> dict[str, object]:
        editor = self.current_editor
        commands: dict[str, object] = {
            "New buffer": self.action_new_buffer,
            "Open file…": self.action_open_file,
            "Save file": self.action_save_file,
            "Save file as…": self.action_save_file_as,
            "Find": self.action_find,
            "Replace": self.action_replace,
            "Go to line": self.action_goto_line,
            "Next buffer": self.action_next_buffer,
            "Previous buffer": self.action_previous_buffer,
            "Undo": lambda: editor.action_undo() if editor else None,
            "Redo": lambda: editor.action_redo() if editor else None,
            "Select all": lambda: editor.action_select_all() if editor else None,
            "Hover documentation": self.action_hover,
            "Go to definition": self.action_definition,
            "Quit": self.action_quit,
        }
        commands.update(self.plugin_commands)
        return commands

    # -------------------------------------------------------------- prompts
    def open_path(self, value: str) -> None:
        self.query_one("#promptbar").close()
        path = Path(value).expanduser()
        for index, buffer in enumerate(self.buffers):
            if buffer.path is not None and buffer.path.resolve() == path.resolve():
                self.set_active(index)
                return
        if path.is_dir():
            self.notify(f"Is a directory: {path}", severity="warning")
            return
        if not path.exists():
            self.notify(f"Creating new file: {path}", severity="warning")
        self._open_buffer(path)
        self.set_active(len(self.buffers) - 1)

    def save_path(self, value: str) -> None:
        self.query_one("#promptbar").close()
        buffer = self.active_buffer
        if buffer is None:
            return
        path = Path(value).expanduser()
        try:
            buffer.save(path)
        except OSError as exc:
            self.notify(f"Could not save: {exc}", severity="error")
            return
        self.notify(f"Saved {buffer.name}")
        self._notify_lsp_save(buffer)
        self._refresh_tabs()
        self._refresh_git()

    def goto_line_number(self, value: str) -> None:
        self.query_one("#promptbar").close()
        editor = self.current_editor
        if editor is None:
            return
        try:
            row = max(0, int(value) - 1)
        except ValueError:
            self.notify("Not a number", severity="warning")
            return
        last_row = max(0, len(editor.text.split("\n")) - 1)
        editor.move_cursor((min(row, last_row), 0))
        editor.scroll_cursor_visible()

    def _word_at_cursor(self, editor: CodeEditor) -> str:
        from demo import search

        text = editor.text
        index = search.location_to_index(text, editor.selection.end)

        def is_word_char(char: str) -> bool:
            return char.isalnum() or char == "_"

        left = index
        while left > 0 and is_word_char(text[left - 1]):
            left -= 1
        right = index
        while right < len(text) and is_word_char(text[right]):
            right += 1
        return text[left:right]
