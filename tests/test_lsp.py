"""Tests for the LSP client using a fake in-memory server."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from demo.lsp import LanguageServer, uri_to_path

FAKE_SERVER = str(Path(__file__).parent / "fake_lsp.py")


class FakeApp:
    """Stands in for the parts of EditorApp the client touches."""

    def __init__(self) -> None:
        self.notifications: list[tuple[str, str]] = []
        self.diagnostics_update: list[str] = []

    def notify(self, message: str, severity: str = "information") -> None:
        self.notifications.append((severity, message))

    def on_diagnostics_update(self, uri: str) -> None:
        self.diagnostics_update.append(uri)

    def set_timer(self, delay, callback) -> None:
        self._timer = (delay, callback)


async def wait_until(predicate, timeout=5.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.01)
    return False


@pytest.mark.asyncio
async def test_lsp_handshake_and_diagnostics():
    app = FakeApp()
    server = LanguageServer(app, [sys.executable, FAKE_SERVER], "python")
    ok = await server.start()
    assert ok is True
    try:
        uri = "file:///tmp/example.py"
        server.did_open(uri, "python", "x = 1\n")
        assert await wait_until(lambda: uri in server.diagnostics), "no diagnostics published"
        diagnostics = server.diagnostics[uri]
        assert len(diagnostics) == 1
        assert diagnostics[0].message == "fake error"
        assert uri in app.diagnostics_update
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_lsp_hover():
    app = FakeApp()
    server = LanguageServer(app, [sys.executable, FAKE_SERVER], "python")
    ok = await server.start()
    assert ok is True
    try:
        content = await server.hover("file:///tmp/example.py", (0, 0))
        assert content == "**hover docs**"
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_lsp_definition():
    app = FakeApp()
    server = LanguageServer(app, [sys.executable, FAKE_SERVER], "python")
    ok = await server.start()
    assert ok is True
    try:
        target = await server.definition("file:///tmp/example.py", (0, 0))
        assert target == ("file:///def.py", 3, 2)
        assert uri_to_path(target[0]) == Path("/def.py")
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_lsp_missing_binary():
    app = FakeApp()
    server = LanguageServer(app, ["/nonexistent/bin/definitely-not-a-server"], "python")
    ok = await server.start()
    assert ok is False
    await server.stop()
