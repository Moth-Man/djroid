"""Title bar widget for the djroid GUI."""

from textual.app import ComposeResult
from textual.widgets import Static


class TitleBar(Static):
    """Title bar at the very top of the application."""

    def compose(self) -> ComposeResult:
        yield Static("dj-en v1.0.0", id="app-title")
