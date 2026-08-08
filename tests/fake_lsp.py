#!/usr/bin/env python3
"""A tiny fake LSP server used only by the test suite."""

import json
import sys


def send(msg):
    payload = json.dumps(msg).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload)
    sys.stdout.buffer.flush()


def recv():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        key, _, value = line.decode("utf-8").partition(":")
        headers[key.strip().lower()] = value.strip()
    if not headers:
        return None
    length = int(headers.get("content-length", 0))
    body = sys.stdin.buffer.read(length)
    return json.loads(body)


while True:
    msg = recv()
    if not msg:
        break
    method = msg.get("method")
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"capabilities": {"hoverProvider": True, "definitionProvider": True}}})
    elif method == "textDocument/hover":
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"contents": {"kind": "markdown", "value": "**hover docs**"}}})
    elif method == "textDocument/definition":
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"uri": "file:///def.py", "range": {"start": {"line": 3, "character": 2}, "end": {"line": 3, "character": 5}}}})
    elif method == "textDocument/didOpen":
        uri = msg["params"]["textDocument"]["uri"]
        send({"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics", "params": {"uri": uri, "diagnostics": [{"range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}}, "severity": 1, "message": "fake error"}]}})
    elif msg.get("id") is not None:
        send({"jsonrpc": "2.0", "id": msg["id"], "result": None})
