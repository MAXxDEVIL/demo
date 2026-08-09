"""Tests for the user-facing improvements: close buffer, safe quit, live
find, kill-ring cycling, replace-all confirmation, and path completion."""

from __future__ import annotations

import pytest

from demo.app import EditorApp
from demo.config import Config


def make_app(config: Config | None = None) -> EditorApp:
    return EditorApp(files=[], config=config or Config())


@pytest.mark.asyncio
async def test_hint_bar_shown_for_empty_untitled():
    app = make_app()
    async with app.run_test() as pilot:
        assert app.query_one("#hintbar").display is True
        app.current_editor.load_text("hello")
        await pilot.pause()
        app.refresh_status()
        await pilot.pause()
        assert app.query_one("#hintbar").display is False


@pytest.mark.asyncio
async def test_tab_close_button_closes_buffer():
    app = make_app()
    async with app.run_test() as pilot:
        app.action_new_buffer()
        await pilot.pause()
        assert len(app.buffers) == 2
        app.query_one("#tab-close-1").press()
        await pilot.pause()
        assert len(app.buffers) == 1


@pytest.mark.asyncio
async def test_close_buffer_clean_closes_immediately():
    app = make_app()
    async with app.run_test() as pilot:
        app.action_new_buffer()
        await pilot.pause()
        assert len(app.buffers) == 2
        app.action_close_buffer()
        await pilot.pause()
        assert len(app.buffers) == 1
        assert not app._dialog_visible


@pytest.mark.asyncio
async def test_close_buffer_discard_keeps_others():
    app = make_app()
    async with app.run_test() as pilot:
        app.action_new_buffer()
        await pilot.pause()
        app.current_editor.load_text("unsaved")
        await pilot.pause()
        assert app.active_buffer.is_modified
        app.action_close_buffer()
        await pilot.pause()
        assert app._dialog_visible
        app.query_one("#dialog")._finish("discard")
        await pilot.pause()
        assert len(app.buffers) == 1
        assert not app._dialog_visible


@pytest.mark.asyncio
async def test_close_buffer_save_saves_and_closes(tmp_path):
    target = tmp_path / "keep.txt"
    target.write_text("original")
    app = EditorApp(files=[str(target)], config=Config())
    async with app.run_test() as pilot:
        app.current_editor.load_text("edited")
        await pilot.pause()
        app.action_close_buffer()
        await pilot.pause()
        assert app._dialog_visible
        app.query_one("#dialog")._finish("save")
        await pilot.pause()
        assert target.read_text() == "edited"
        assert not app._dialog_visible
        assert app.current_editor is not None


@pytest.mark.asyncio
async def test_close_buffer_save_untitled_opens_save_as():
    app = make_app()
    async with app.run_test() as pilot:
        app.current_editor.load_text("scratch")
        await pilot.pause()
        app.action_close_buffer()
        await pilot.pause()
        app.query_one("#dialog")._finish("save")
        await pilot.pause()
        assert app.query_one("#promptbar").display is True
        assert len(app.buffers) == 1


@pytest.mark.asyncio
async def test_quit_no_changes_exits_immediately():
    app = make_app()
    async with app.run_test() as pilot:
        exited = []
        app._quit = lambda: exited.append(True)
        app.action_quit()
        await pilot.pause()
        assert not app._dialog_visible
        assert exited


@pytest.mark.asyncio
async def test_quit_cancel_keeps_buffers():
    app = make_app()
    async with app.run_test() as pilot:
        app.current_editor.load_text("x")
        await pilot.pause()
        app.action_quit()
        await pilot.pause()
        assert app._dialog_visible
        app.query_one("#dialog")._finish("cancel")
        await pilot.pause()
        assert not app._dialog_visible
        assert len(app.buffers) == 1


@pytest.mark.asyncio
async def test_quit_discard_all():
    app = make_app()
    async with app.run_test() as pilot:
        app.current_editor.load_text("x")
        await pilot.pause()
        exited = []
        app._quit = lambda: exited.append(True)
        app.action_quit()
        await pilot.pause()
        app.query_one("#dialog")._finish("discard_all")
        await pilot.pause()
        assert exited


@pytest.mark.asyncio
async def test_quit_save_all_saves_then_quits(tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("old")
    app = EditorApp(files=[str(target)], config=Config())
    async with app.run_test() as pilot:
        app.current_editor.load_text("new")
        await pilot.pause()
        exited = []
        app._quit = lambda: exited.append(True)
        app.action_quit()
        await pilot.pause()
        app.query_one("#dialog")._finish("save_all")
        await pilot.pause()
        assert target.read_text() == "new"
        assert exited


@pytest.mark.asyncio
async def test_quit_save_all_untitled_defers_to_save_as(tmp_path):
    app = make_app()
    async with app.run_test() as pilot:
        app.current_editor.load_text("scratch")
        await pilot.pause()
        app.action_quit()
        await pilot.pause()
        app.query_one("#dialog")._finish("save_all")
        await pilot.pause()
        assert app._quit_pending
        assert app.query_one("#promptbar").display is True
        exited = []
        app._quit = lambda: exited.append(True)
        app.save_path(str(tmp_path / "u.txt"))
        await pilot.pause()
        assert not app._quit_pending
        assert exited
        assert (tmp_path / "u.txt").read_text() == "scratch"


@pytest.mark.asyncio
async def test_find_updates_live():
    app = make_app()
    async with app.run_test() as pilot:
        editor = app.current_editor
        editor.load_text("the quick brown fox brown")
        await pilot.pause()
        app.action_find()
        await pilot.pause()
        find_input = app.query_one("#find-input")
        find_input.value = "brown"
        await pilot.pause()
        assert editor.selected_text == "brown"


@pytest.mark.asyncio
async def test_find_case_toggle():
    app = make_app()
    async with app.run_test() as pilot:
        editor = app.current_editor
        editor.load_text("Foo foo FOO")
        await pilot.pause()
        app.action_find()
        await pilot.pause()
        find_input = app.query_one("#find-input")
        find_input.value = "foo"
        await pilot.pause()
        findbar = app.query_one("#findbar")
        assert findbar._case_sensitive is False
        assert findbar._total == 3
        findbar.toggle_case()
        await pilot.pause()
        assert findbar._case_sensitive is True
        assert findbar._total == 1
        findbar.toggle_case()
        await pilot.pause()
        assert findbar._case_sensitive is False
        assert findbar._total == 3


@pytest.mark.asyncio
async def test_replace_all_confirms_then_replaces():
    app = make_app()
    async with app.run_test() as pilot:
        editor = app.current_editor
        editor.load_text("a a a")
        await pilot.pause()
        app.action_replace()
        await pilot.pause()
        app.query_one("#find-input").value = "a"
        app.query_one("#replace-input").value = "b"
        await pilot.pause()
        findbar = app.query_one("#findbar")
        findbar.replace_all()
        await pilot.pause()
        assert app._dialog_visible
        app.query_one("#dialog")._finish("confirm")
        await pilot.pause()
        assert editor.text == "b b b"


@pytest.mark.asyncio
async def test_replace_all_cancel_does_nothing():
    app = make_app()
    async with app.run_test() as pilot:
        editor = app.current_editor
        editor.load_text("a a a")
        await pilot.pause()
        app.action_replace()
        await pilot.pause()
        app.query_one("#find-input").value = "a"
        app.query_one("#replace-input").value = "b"
        await pilot.pause()
        app.query_one("#findbar").replace_all()
        await pilot.pause()
        app.query_one("#dialog")._finish("cancel")
        await pilot.pause()
        assert editor.text == "a a a"


@pytest.mark.asyncio
async def test_prompt_complete_cycles(tmp_path):
    (tmp_path / "foo1.txt").write_text("")
    (tmp_path / "foo2.txt").write_text("")
    app = make_app()
    async with app.run_test() as pilot:
        app.query_one("#promptbar").open("open", "Open: ", str(tmp_path / "foo"))
        await pilot.pause()
        bar = app.query_one("#promptbar")
        bar.complete()
        await pilot.pause()
        bar.complete()
        await pilot.pause()
        value = bar.query_one("#prompt-input").value
        assert value in {str(tmp_path / "foo1.txt"), str(tmp_path / "foo2.txt")}
        bar.complete()
        await pilot.pause()
        assert bar.query_one("#prompt-input").value == value


@pytest.mark.asyncio
async def test_yank_pop_cycles():
    from textual.app import App, ComposeResult

    from demo.widgets.code_editor import CodeEditor

    class Harness(App[None]):
        def compose(self) -> ComposeResult:
            yield CodeEditor(language="python")

        @property
        def editor(self) -> CodeEditor:
            return self.query_one(CodeEditor)

    harness = Harness()
    async with harness.run_test() as pilot:
        editor = harness.editor
        CodeEditor.kill_ring.clear()
        editor.load_text("abc")
        editor._kill("first")
        editor._kill("second")
        await pilot.pause()
        editor.action_yank()
        await pilot.pause()
        assert editor.text == "secondabc"
        editor.action_yank_pop()
        await pilot.pause()
        assert editor.text == "firstabc"


def test_command_shortcuts_include_bindings():
    app = make_app()
    shortcuts = app.command_shortcuts()
    assert shortcuts.get("Save file") == "ctrl+o"
    assert shortcuts.get("Close buffer") == "ctrl+shift+w"
    assert shortcuts.get("Quit") == "ctrl+x"
