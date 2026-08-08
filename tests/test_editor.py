"""Tests for the CodeEditor widget and the editor app."""

from __future__ import annotations

import asyncio
import functools

import pytest
from textual.app import App, ComposeResult
from textual.document._document import Selection

from demo.app import EditorApp
from demo.config import Config
from demo.widgets.code_editor import CodeEditor


class EditorHarness(App[None]):
    """A minimal app that hosts a single CodeEditor."""

    def __init__(self, language: str | None = None) -> None:
        super().__init__()
        self.language = language

    def compose(self) -> ComposeResult:
        yield CodeEditor(language=self.language)

    @property
    def editor(self) -> CodeEditor:
        return self.query_one(CodeEditor)


def editor_test(language: str | None = None, text: str = ""):
    """Run a test against a fresh CodeEditor with *text* loaded and cursor home."""

    def decorator(fn):
        @functools.wraps(fn)
        @pytest.mark.asyncio
        async def wrapper():
            await _run(fn, language, text)

        return wrapper

    return decorator


@pytest.mark.asyncio
async def test_kill_line_into_kill_ring():
    async def body(harness, editor, pilot):
        editor.action_kill_line()
        await pilot.pause()
        assert editor.text == "second line"
        assert CodeEditor.kill_ring[-1] == "hello world"

    await _run(body, "python", "hello world\nsecond line")


@pytest.mark.asyncio
async def test_kill_empty_line_kills_newline():
    async def body(harness, editor, pilot):
        editor.move_cursor((0, 5))
        editor.action_kill_line()  # at EOL -> kills the newline
        await pilot.pause()
        assert editor.text == "firstsecond"
        assert CodeEditor.kill_ring[-1] == "\n"

    await _run(body, "python", "first\nsecond")


@pytest.mark.asyncio
async def test_yank_restores_killed_text():
    async def body(harness, editor, pilot):
        editor.action_kill_line()
        await pilot.pause()
        editor.move_cursor((0, 0))
        editor.action_yank()
        await pilot.pause()
        assert editor.text == "abc def"

    await _run(body, "python", "abc def")


@pytest.mark.asyncio
async def test_cut_selection():
    async def body(harness, editor, pilot):
        editor.selection = Selection((0, 1), (0, 3))
        editor.action_cut_selection()
        await pilot.pause()
        assert editor.text == "adef"
        assert CodeEditor.kill_ring[-1] == "bc"

    await _run(body, "python", "abcdef")


@pytest.mark.asyncio
async def test_cut_whole_line():
    async def body(harness, editor, pilot):
        editor.move_cursor((1, 0))
        editor.action_cut_selection()  # no selection -> cut whole line
        await pilot.pause()
        assert editor.text == "a\nc\n"
        assert CodeEditor.kill_ring[-1] == "b\n"

    await _run(body, "python", "a\nb\nc\n")


@pytest.mark.asyncio
async def test_transpose_chars():
    async def body(harness, editor, pilot):
        editor.move_cursor((0, 1))
        editor.action_transpose_chars()
        await pilot.pause()
        assert editor.text == "ba cd"

    await _run(body, "python", "ab cd")


@pytest.mark.asyncio
async def test_toggle_comment_on():
    async def body(harness, editor, pilot):
        editor.action_toggle_comment()
        await pilot.pause()
        assert editor.text == "# print(1)"

    await _run(body, "python", "print(1)")


@pytest.mark.asyncio
async def test_toggle_comment_off():
    async def body(harness, editor, pilot):
        editor.action_toggle_comment()
        await pilot.pause()
        assert editor.text == "print(1)"

    await _run(body, "python", "# print(1)")


@pytest.mark.asyncio
async def test_unindent_line():
    async def body(harness, editor, pilot):
        editor.indent_width = 4
        editor.action_unindent_line()
        await pilot.pause()
        assert editor.text == "    x"

    await _run(body, "python", "        x")


@pytest.mark.asyncio
async def test_undo_redo():
    async def body(harness, editor, pilot):
        editor.move_cursor((0, 3))
        editor.insert("d")
        await pilot.pause()
        assert editor.text == "abcd"
        editor.undo()
        await pilot.pause()
        assert editor.text == "abc"
        editor.redo()
        await pilot.pause()
        assert editor.text == "abcd"

    await _run(body, "python", "abc")


async def _run(body, language, text):
    harness = EditorHarness(language)
    async with harness.run_test() as pilot:
        editor = harness.editor
        editor.load_text(text)
        editor.move_cursor((0, 0))
        await pilot.pause()
        try:
            await body(harness, editor, pilot)
        finally:
            CodeEditor.kill_ring.clear()


@pytest.mark.asyncio
async def test_app_new_buffer_and_switch():
    config = Config()
    app = EditorApp(files=[], config=config)
    async with app.run_test() as pilot:
        app.action_new_buffer()
        await pilot.pause()
        assert len(app.buffers) == 2
        first = app.buffers[0]
        app.set_active(0)
        await pilot.pause()
        assert first.editor.display is True
        assert app.buffers[1].editor.display is False
        app.action_next_buffer()
        await pilot.pause()
        assert app.active_buffer is app.buffers[1]


@pytest.mark.asyncio
async def test_app_save_via_prompt(tmp_path):
    config = Config()
    app = EditorApp(files=[], config=config)
    target = tmp_path / "out.txt"
    async with app.run_test() as pilot:
        editor = app.current_editor
        editor.load_text("hello demo")
        await pilot.pause()
        app.save_path(str(target))
        await pilot.pause()
        assert target.read_text() == "hello demo"
        assert app.active_buffer.is_modified is False


@pytest.mark.asyncio
async def test_app_open_path(tmp_path):
    config = Config()
    source = tmp_path / "in.txt"
    source.write_text("some content")
    app = EditorApp(files=[], config=config)
    async with app.run_test() as pilot:
        app.open_path(str(source))
        await pilot.pause()
        assert app.current_editor.text == "some content"


@pytest.mark.asyncio
async def test_move_line_down():
    async def body(harness, editor, pilot):
        editor.move_cursor((0, 1))
        editor.action_move_line_down()
        await pilot.pause()
        assert editor.text == "b\na\nc"
        assert editor.selection.end == (1, 1)

    await _run(body, "python", "a\nb\nc")


@pytest.mark.asyncio
async def test_move_line_up():
    async def body(harness, editor, pilot):
        editor.move_cursor((2, 0))
        editor.action_move_line_up()
        await pilot.pause()
        assert editor.text == "a\nc\nb"

    await _run(body, "python", "a\nb\nc")


@pytest.mark.asyncio
async def test_duplicate_line():
    async def body(harness, editor, pilot):
        editor.move_cursor((1, 1))
        editor.action_duplicate_line()
        await pilot.pause()
        assert editor.text == "a\nb\nb\nc"

    await _run(body, "python", "a\nb\nc")


@pytest.mark.asyncio
async def test_select_next_occurrence():
    async def body(harness, editor, pilot):
        editor.load_text("foo bar foo")
        editor.move_cursor((0, 1))
        editor.action_select_next_occurrence()
        await pilot.pause()
        assert editor.selected_text == "foo"
        editor.action_select_next_occurrence()
        await pilot.pause()
        assert editor.selected_text == "foo"
        assert editor.selection.end == (0, 11)

    await _run(body, "python", "foo bar")


@pytest.mark.asyncio
async def test_reload_if_clean(tmp_path):
    from demo.buffers import Buffer

    path = tmp_path / "f.txt"
    path.write_text("v1")
    app = EditorApp(files=[str(path)], config=Config())
    async with app.run_test() as pilot:
        assert app.current_editor.text == "v1"
        path.write_text("v2")
        buffer = app.active_buffer
        assert buffer.has_external_changes() is True
        assert buffer.reload_if_clean() is True
        await pilot.pause()
        assert app.current_editor.text == "v2"


@pytest.mark.asyncio
async def test_reload_keeps_edits(tmp_path):
    path = tmp_path / "f.txt"
    path.write_text("v1")
    app = EditorApp(files=[str(path)], config=Config())
    async with app.run_test() as pilot:
        editor = app.current_editor
        editor.load_text("my edit")
        await pilot.pause()
        path.write_text("v2")
        buffer = app.active_buffer
        assert buffer.reload_if_clean() is False
        assert app.current_editor.text == "my edit"


@pytest.mark.asyncio
async def test_app_find_selects_match():
    config = Config()
    app = EditorApp(files=[], config=config)
    async with app.run_test() as pilot:
        editor = app.current_editor
        editor.load_text("the quick brown fox")
        await pilot.pause()
        app.action_find()
        await pilot.pause()
        find_input = app.query_one("#find-input")
        find_input.value = "brown"
        await pilot.pause()
        findbar = app.query_one("#findbar")
        findbar.find_next()
        await pilot.pause()
        assert editor.selected_text == "brown"


@pytest.mark.asyncio
async def test_app_palette_runs_command():
    config = Config()
    app = EditorApp(files=[], config=config)
    async with app.run_test() as pilot:
        palette = app.query_one("#palette")
        palette.set_commands(app.commands())
        palette.open()
        await pilot.pause()
        assert palette.display is True
        palette.query_one("#palette-input").value = "Next buffer"
        await pilot.pause()
        before = app.active_index
        palette.run_highlighted()
        await pilot.pause()
        assert app.active_index == (before + 1) % len(app.buffers)


@pytest.mark.asyncio
async def test_app_goto_line():
    config = Config()
    app = EditorApp(files=[], config=config)
    async with app.run_test() as pilot:
        editor = app.current_editor
        editor.load_text("one\ntwo\nthree")
        await pilot.pause()
        app.goto_line_number("2")
        await pilot.pause()
        assert editor.selection.end == (1, 0)
