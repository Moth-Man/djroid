"""Navigation header widget for the dj-en GUI."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Button


class NavigationHeader(Static):
    """Navigation header with tabs for different views."""

    def compose(self) -> ComposeResult:
        with Horizontal(id="nav-buttons"):
            yield Button("Library", id="btn-library", variant="primary")
            yield Button("Chat", id="btn-chat")
            yield Button("Settings", id="btn-settings")
