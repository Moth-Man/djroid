"""Command palette footer widget for the dj-en GUI."""

from textual.app import ComposeResult
from textual.widgets import Static


class CommandPalette(Static):
    """Command palette footer showing available commands."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #888888]^l[/] library   [bold #888888]^c[/] chat   "
            "[bold #888888]^s[/] settings   [bold #888888]^h[/] help   [bold #888888]^q[/] quit",
            id="command-palette-text"
        )
