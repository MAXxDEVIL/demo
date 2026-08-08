"""A small plugin system.

Plugins are plain Python files in ``~/.config/demo/plugins/``.  A plugin may
define an ``init(api)`` function that receives a :class:`PluginApi` and
registers commands and hooks::

    def init(api):
        api.register_command("Hello world", lambda: api.notify("Hi from plugin"))

Hook functions (``on_load``, ``on_save``, ...) may also be defined at module
level and will be called by the application.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from demo.app import EditorApp


class PluginApi:
    """The interface exposed to plugins."""

    def __init__(self, app: "EditorApp") -> None:
        self.app = app

    def register_command(self, name: str, action: Callable[[], None]) -> None:
        """Add *name* to the command palette (``Alt+X``)."""
        self.app.plugin_commands[name] = action

    def notify(self, message: str, severity: str = "information") -> None:
        self.app.notify(message, severity=severity)

    @property
    def config(self):
        return self.app.config

    @property
    def buffers(self):
        return self.app.buffers

    @property
    def active_buffer(self):
        return self.app.active_buffer


class PluginManager:
    """Loads plugin modules and dispatches hooks to them."""

    def __init__(self, app: "EditorApp") -> None:
        self.app = app
        self.modules: list[object] = []

    def load_directory(self, directory: str | Path) -> int:
        """Import every ``*.py`` in *directory*, calling ``init(api)`` on each."""
        directory = Path(directory)
        if not directory.is_dir():
            return 0
        loaded = 0
        for path in sorted(directory.glob("*.py")):
            if path.name.startswith("_"):
                continue
            module = self._load_module(path)
            if module is None:
                continue
            self.modules.append(module)
            loaded += 1
            init = getattr(module, "init", None)
            if callable(init):
                try:
                    init(PluginApi(self.app))
                except Exception as exc:  # noqa: BLE001 - plugins are untrusted
                    self.app.notify(f"Plugin {path.name} failed to init: {exc}", severity="error")
        return loaded

    def _load_module(self, path: Path) -> object | None:
        spec = importlib.util.spec_from_file_location(f"demo_plugin_{path.stem}", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001
            self.app.notify(f"Could not load plugin {path.name}: {exc}", severity="error")
            return None
        return module

    def run_hook(self, name: str, *args: object) -> None:
        """Call ``on_<name>(*args)`` on every loaded plugin."""
        for module in self.modules:
            hook = getattr(module, f"on_{name}", None)
            if callable(hook):
                try:
                    hook(*args)
                except Exception as exc:  # noqa: BLE001
                    self.app.notify(f"Plugin hook {name} failed: {exc}", severity="error")
