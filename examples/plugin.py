"""Example demo plugin.

Copy this file into ~/.config/demo/plugins/ to enable it.
"""


def init(api):
    """Called once when the plugin is loaded."""
    api.register_command("Say hi", lambda: api.notify("Hi from my plugin!"))

    def count_buffers():
        api.notify(f"You have {len(api.buffers)} open buffer(s).")

    api.register_command("Count buffers", count_buffers)


def on_load(buffer):
    """Called when a buffer is opened."""
    print(f"[plugin] loaded {buffer.name}")


def on_save(buffer):
    """Called after a buffer is saved."""
    print(f"[plugin] saved {buffer.name}")
