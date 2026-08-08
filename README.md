# demo

A full-featured **modeless** CLI code editor for the terminal, written in Python
on top of [Textual](https://textual.textualize.io/).

`demo` is keyboard-first and modeless (nano/Emacs style — no mode switching):
you type text and press `Ctrl`-combinations for commands.

## Features

- **Editing** — Emacs-style kill ring (`Ctrl+K` kill, `Ctrl+W` cut, `Ctrl+U` yank),
  undo/redo, selection, transpose characters, comment toggle, indent/unindent,
  move/duplicate lines, select-next-occurrence.
- **Multiple buffers** — tabs, `Ctrl+Tab` cycling, `Alt+1..9` jumps, buffer list
  in the command palette, auto-reload on external changes (never clobbers edits).
- **Search** — incremental find (`Ctrl+F`) and query replace (`Ctrl+R`), with
  wrap-around and match counts.
- **Syntax highlighting** — built-in tree-sitter highlighting for Python,
  JavaScript/TypeScript, Rust, Go, JSON, TOML, YAML, Markdown, HTML, CSS, SQL,
  Bash and more. Five color themes.
- **Git integration** — current branch and dirty state in the status bar.
- **Language servers (LSP)** — diagnostics count, hover documentation (`Alt+H`),
  and go-to-definition (`Alt+.`).
- **Command palette** — fuzzy command switcher with `Alt+X`.
- **Plugins** — drop Python files in `~/.config/demo/plugins/` to add commands.
- **Configuration** — `~/.config/demo/config.toml`.

## Install

```bash
cd demo
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/demo path/to/file.py
```

Or run without installing: `.venv/bin/python -m demo file.py`.

## Keybindings

### Editing

| Keys | Action |
| --- | --- |
| `Ctrl+K` | Kill line into kill ring |
| `Ctrl+W` | Cut selection (whole line if none) |
| `Ctrl+U` | Paste (yank) |
| `Ctrl+Z` / `Ctrl+Shift+Z` | Undo / redo |
| `Ctrl+D` / `Backspace` | Delete right / left |
| `Alt+D` | Delete word right |
| `Alt+T` | Transpose characters |
| `Alt+/` | Toggle line comment |
| `Tab` / `Shift+Tab` | Indent / unindent |
| `Alt+N` | Select next occurrence |
| `Alt+Up` / `Alt+Down` | Move line up / down |
| `Alt+Shift+D` | Duplicate line |

### Movement

| Keys | Action |
| --- | --- |
| `Ctrl+B` / `Ctrl+F` | Character left / right |
| `Ctrl+P` / `Ctrl+N` | Line up / down |
| `Ctrl+A` / `Ctrl+E` | Line start / end |
| `Alt+B` / `Alt+F` | Word left / right |
| `Ctrl+Home` / `Ctrl+End` | Document start / end |
| `PageUp` / `PageDown` | Page up / down |
| `Shift+arrows` | Extend selection |

### Buffers

| Keys | Action |
| --- | --- |
| `Ctrl+T` | Open file |
| `Ctrl+O` | Save file |
| `Ctrl+Shift+S` | Save as |
| `Ctrl+Tab` | Next buffer |
| `Ctrl+Shift+Tab` | Previous buffer |
| `Alt+1` … `Alt+9` | Jump to buffer |

### Search

| Keys | Action |
| --- | --- |
| `Ctrl+F` | Find (`Enter` next, `Ctrl+P` previous, `Esc` close) |
| `Ctrl+R` | Query replace (`Enter` replace + next, `Alt+A` replace all) |
| `Ctrl+G` | Go to line |

### App

| Keys | Action |
| --- | --- |
| `Alt+X` | Command palette |
| `Alt+H` | Hover documentation |
| `Alt+.` | Go to definition |
| `F1` | Keybinding reference |
| `Ctrl+X` / `Ctrl+Q` | Quit |

Press `F1` inside the editor for a full reference.

## Configuration

Create `~/.config/demo/config.toml`:

```toml
theme = "vscode_dark"        # css | dracula | github_light | monokai | vscode_dark
soft_wrap = false
show_line_numbers = true
indent_width = 4
highlight_cursor_line = true
case_sensitive_search = false

[lsp]
# "python" = ["pyright-langserver", "--stdio"]
```

Language servers are started lazily per language when a matching file becomes
active. Any command that speaks LSP over stdio works.

## Plugins

Drop a `.py` file into `~/.config/demo/plugins/` (create it if needed). A plugin
exposes an `init(api)` function:

```python
def init(api):
    api.register_command("Say hi", lambda: api.notify("Hi from my plugin!"))
```

Hook functions (`on_load(buffer)`, `on_save(buffer)`) can also be defined at
module level. See `examples/plugin.py`.

## Development

```bash
.venv/bin/pip install -e ".[test]"   # or: pip install pytest pytest-asyncio
.venv/bin/python -m pytest
```

The test suite covers the pure search/index logic, the editor widget actions,
the app workflows, and the LSP client (against a fake in-memory server).

## Layout

```
demo/
  app.py            # EditorApp: layout, actions, buffer + LSP wiring
  buffers.py        # Buffer: file path, dirty tracking, load/save/reload
  cli.py            # entry point
  config.py         # TOML configuration
  git_integration.py# branch + dirty status via `git`
  keymap.py         # single source of truth for bindings and help
  lsp.py            # minimal LSP client over stdio
  plugins.py        # plugin loader and hook dispatch
  search.py         # pure find/replace helpers
  syntax.py         # extension -> language detection
  themes.py         # theme validation
  widgets/
    code_editor.py  # CodeEditor(TextArea) + kill ring and editor actions
    commandpalette.py, findbar.py, helpview.py, promptbar.py,
    statusbar.py, tabstrip.py
tests/              # pytest suite + a fake LSP server
```
