"""A minimal Language Server Protocol (LSP) client over stdio.

Implements the small slice of LSP demo needs: initialize handshake,
``textDocument/didOpen`` / ``didChange`` / ``didSave`` notifications,
``publishDiagnostics`` handling, hover and go-to-definition requests.
Only one server per language is spawned, lazily, when a file of that language
becomes active.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.parse
from pathlib import Path
from typing import TYPE_CHECKING

from lsprotocol import converters
from lsprotocol.types import Diagnostic, Hover, PublishDiagnosticsParams

_CONVERTER = converters.get_converter()

if TYPE_CHECKING:
    from demo.app import EditorApp

log = logging.getLogger("demo.lsp")

MAX_MESSAGE_LENGTH = 4 * 1024 * 1024


def uri_to_path(uri: str) -> Path:
    """Convert a ``file://`` URI to a filesystem path."""
    parsed = urllib.parse.urlparse(uri)
    return Path(urllib.parse.unquote(parsed.path))


class LanguageServer:
    """One running language-server subprocess and its protocol state."""

    def __init__(self, app: "EditorApp", command: list[str], language: str) -> None:
        self.app = app
        self.command = list(command)
        self.language = language
        self.process: asyncio.subprocess.Process | None = None
        self.stdin = None
        self.stdout = None
        self._reader_task: asyncio.Task | None = None
        self._request_id = 0
        self.pending: dict[int, asyncio.Future] = {}
        self.diagnostics: dict[str, list[Diagnostic]] = {}
        self.version = 0
        self._frame_buffer = b""
        self._pending_change: tuple[str, str, int] | None = None
        self.capabilities: dict = {}

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    async def start(self) -> bool:
        """Spawn the server and run the initialize handshake."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except (FileNotFoundError, PermissionError, OSError) as exc:
            log.warning("could not start %s: %s", self.command, exc)
            return False
        assert self.process.stdin is not None and self.process.stdout is not None
        self.stdin = self.process.stdin
        self.stdout = self.process.stdout
        self._reader_task = asyncio.create_task(self._read_loop())
        result = await self._request(
            "initialize",
            {
                "processId": os.getpid(),
                "rootUri": self._root_uri(),
                "capabilities": {},
                "workspaceFolders": [{"uri": self._root_uri(), "name": "demo"}]
                if self._root_uri()
                else [],
            },
        )
        await self._notify("initialized", {})
        if result:
            self.capabilities = result.get("capabilities", {}) or {}
        return True

    def _root_uri(self) -> str | None:
        cwd = Path.cwd()
        return cwd.resolve().as_uri() if cwd.exists() else None

    # ------------------------------------------------------------- lifecycle
    def kill(self) -> None:
        """Terminate the server process immediately (used on app quit)."""
        if self.process is not None and self.process.returncode is None:
            try:
                self.process.terminate()
            except ProcessLookupError:
                pass
        if self._reader_task is not None:
            self._reader_task.cancel()

    async def stop(self) -> None:
        self._shutdown = True
        if self.is_running:
            try:
                await self._request("shutdown", {})
            except (asyncio.TimeoutError, asyncio.CancelledError, OSError):
                pass
            await self._notify("exit", {})
        if self.process is not None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=2)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
        if self._reader_task is not None:
            self._reader_task.cancel()

    # -------------------------------------------------------------- protocol
    async def _send_message(self, message: dict) -> None:
        if self.stdin is None:
            raise OSError("no stdin")
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
        if len(payload) > MAX_MESSAGE_LENGTH:
            raise OSError("message too large")
        frame = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload
        self.stdin.write(frame)
        await self.stdin.drain()

    async def _request(self, method: str, params: dict):
        self._request_id += 1
        request_id = self._request_id
        future = asyncio.get_running_loop().create_future()
        self.pending[request_id] = future
        await self._send_message({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        try:
            return await asyncio.wait_for(future, timeout=10)
        except asyncio.TimeoutError:
            self.pending.pop(request_id, None)
            raise TimeoutError(f"LSP request {method} timed out")

    async def _notify(self, method: str, params: dict) -> None:
        try:
            await self._send_message({"jsonrpc": "2.0", "method": method, "params": params})
        except OSError:
            pass

    async def _read_loop(self) -> None:
        try:
            while self.is_running and self.stdout is not None:
                header = await self._read_until(b"\r\n\r\n")
                if header is None:
                    break
                length = self._parse_content_length(header)
                if length is None:
                    continue
                body = await self.stdout.readexactly(length)
                message = json.loads(body.decode("utf-8"))
                try:
                    self._handle_message(message)
                except Exception as exc:  # noqa: BLE001
                    log.warning("error handling LSP message: %s", exc)
        except (asyncio.IncompleteReadError, ConnectionResetError, OSError) as exc:
            log.info("LSP %s read loop ended: %s", self.language, exc)
        finally:
            self.pending.clear()
            if self.is_running and self.process is not None:
                self.process.terminate()

    async def _read_until(self, delimiter: bytes) -> bytes | None:
        """Read exactly one delimiter-terminated chunk; ``None`` on EOF."""
        assert self.stdout is not None
        while delimiter not in self._frame_buffer:
            chunk = await self.stdout.read(1)
            if not chunk:
                if not self._frame_buffer:
                    return None
                break
            self._frame_buffer += chunk
        data, _, rest = self._frame_buffer.partition(delimiter)
        self._frame_buffer = rest
        return data + delimiter

    def _parse_content_length(self, header: bytes) -> int | None:
        for line in header.decode("ascii", errors="ignore").split("\r\n"):
            key, sep, value = line.partition(":")
            if sep and key.strip().lower() == "content-length":
                try:
                    return int(value.strip())
                except ValueError:
                    return None
        return None

    def _handle_message(self, message: dict) -> None:
        if "id" in message and "method" not in message:
            future = self.pending.pop(message["id"], None)
            if future is not None and not future.done():
                if "error" in message:
                    future.set_exception(OSError(message["error"]))
                else:
                    future.set_result(message.get("result"))
            return
        method = message.get("method")
        params = message.get("params") or {}
        if method == "textDocument/publishDiagnostics":
            self._on_diagnostics(params)
        elif method == "window/showMessage":
            self.app.notify(str(params.get("message", "")), severity="warning")
        else:
            log.debug("unhandled LSP notification: %s", method)

    def _on_diagnostics(self, params: dict) -> None:
        try:
            parsed = _CONVERTER.structure(params, PublishDiagnosticsParams)
        except Exception as exc:  # noqa: BLE001
            log.warning("bad publishDiagnostics payload: %s", exc)
            return
        self.diagnostics[parsed.uri] = list(parsed.diagnostics or [])
        self.app.on_diagnostics_update(parsed.uri)

    # --------------------------------------------------------------- editing
    def did_open(self, uri: str, language: str, text: str) -> None:
        self.version += 1
        asyncio.ensure_future(
            self._notify(
                "textDocument/didOpen",
                {"textDocument": {"uri": uri, "languageId": language, "version": self.version, "text": text}},
            )
        )

    def did_change(self, uri: str, text: str) -> None:
        self.version += 1
        self._pending_change = (uri, text, self.version)
        self.app.set_timer(0.3, self._flush_change)

    def _flush_change(self) -> None:
        if self._pending_change is None or self.stdin is None:
            return
        uri, text, version = self._pending_change
        self._pending_change = None
        asyncio.ensure_future(
            self._notify(
                "textDocument/didChange",
                {"textDocument": {"uri": uri, "version": version}, "contentChanges": [{"text": text}]},
            )
        )

    def did_save(self, uri: str) -> None:
        asyncio.ensure_future(self._notify("textDocument/didSave", {"textDocument": {"uri": uri}}))

    def did_close(self, uri: str) -> None:
        asyncio.ensure_future(self._notify("textDocument/didClose", {"textDocument": {"uri": uri}}))
        self.diagnostics.pop(uri, None)

    # -------------------------------------------------------------- queries
    async def hover(self, uri: str, position: tuple[int, int]) -> str | None:
        result = await self._request(
            "textDocument/hover",
            {"textDocument": {"uri": uri}, "position": {"line": position[0], "character": position[1]}},
        )
        if not result:
            return None
        hover = _CONVERTER.structure(result, Hover)
        contents = hover.contents
        if hasattr(contents, "value"):
            return contents.value
        if isinstance(contents, str):
            return contents
        return str(contents)

    async def definition(self, uri: str, position: tuple[int, int]) -> tuple[str, int, int] | None:
        result = await self._request(
            "textDocument/definition",
            {"textDocument": {"uri": uri}, "position": {"line": position[0], "character": position[1]}},
        )
        if not result:
            return None
        locations = result if isinstance(result, list) else [result]
        for location in locations:
            if not location:
                continue
            if "targetUri" in location:  # LocationLink
                target_uri = location["targetUri"]
                target_range = location.get("targetRange") or location.get("range")
            else:  # Location
                target_uri = location.get("uri")
                target_range = location.get("range")
            if target_uri and target_range:
                start = target_range.get("start", {})
                return target_uri, int(start.get("line", 0)), int(start.get("character", 0))
        return None
