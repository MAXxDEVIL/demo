"""Buffer: one open file/scratch buffer and its owning editor widget."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from demo.syntax import detect_language

if TYPE_CHECKING:
    from demo.widgets.code_editor import CodeEditor


class Buffer:
    """A document tied to a file path (or a scratch buffer) and a ``CodeEditor``.

    The editor widget owns the actual text, cursor, selection and history; the
    buffer adds the file-system concerns (name, language, dirty tracking,
    load/save).
    """

    def __init__(self, path: str | Path | None, editor: "CodeEditor") -> None:
        self.path = Path(path) if path else None
        self.editor = editor
        self._saved_text: str | None = None
        self._mtime: float | None = None

    @property
    def name(self) -> str:
        if self.path is None:
            return "untitled"
        return self.path.name

    @property
    def language(self) -> str | None:
        return detect_language(self.path)

    @property
    def is_modified(self) -> bool:
        return self._saved_text is None or self.editor.text != self._saved_text

    def load(self) -> None:
        """Read the file from disk into the editor."""
        if self.path is not None and self.path.exists():
            try:
                text = self.path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
        else:
            text = ""
        self.editor.load_text(text)
        self.editor.move_cursor((0, 0))
        self._saved_text = text
        self._mtime = self.path.stat().st_mtime if self.path is not None and self.path.exists() else None

    def has_external_changes(self) -> bool:
        """Return ``True`` if the file changed on disk since it was loaded."""
        if self.path is None or not self.path.exists():
            return False
        try:
            return self.path.stat().st_mtime != self._mtime
        except OSError:
            return False

    def reload_if_clean(self) -> bool:
        """Reload the file from disk, but only if the buffer has no edits."""
        if self.path is None or not self.path.exists():
            return False
        if self.is_modified or not self.has_external_changes():
            return False
        self.load()
        return True

    def save(self, path: str | Path | None = None) -> Path | None:
        """Write the editor text to *path* (or the buffer's own path)."""
        if path is not None:
            self.path = Path(path)
        if self.path is None:
            return None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.editor.text, encoding="utf-8")
        self._saved_text = self.editor.text
        return self.path
