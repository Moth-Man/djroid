"""Playlist panel widget for the djroid GUI."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, Tree


class PlaylistPanel(Static):
    """Left panel showing playlist tree structure."""

    def on_mount(self) -> None:
        """Set the border title when mounted."""
        self.border_title = "Playlists"

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("PLAYLISTS", classes="panel-header")
            tree = Tree("Root")
            tree.root.expand()
            tree.root.add_leaf("House Classics")
            tree.root.add_leaf("Tech House")
            tree.root.add_leaf("Deep House")
            favorites = tree.root.add("Favorites")
            favorites.add_leaf("Top 100")
            favorites.add_leaf("Recent Finds")
            yield tree
