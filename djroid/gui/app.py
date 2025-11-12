"""Main Djroid GUI application."""

from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal

from .messages import SongSelected, SongTagsUpdated
from .panels.title_bar import TitleBar
from .panels.navigation import NavigationHeader
from .panels.command_palette import CommandPalette
from .panels.playlists import PlaylistPanel
from .panels.songs import SongsPanel
from .panels.tags import TagSchemaPanel


class DjroidGUI(App):
    """Main Djroid GUI application."""

    CSS_PATH = Path(__file__).parent / "styles.tcss"

    def compose(self) -> ComposeResult:
        with Vertical():
            yield TitleBar(id="title-bar")
            yield NavigationHeader(id="nav-header")
            with Horizontal(id="main-container"):
                yield PlaylistPanel(classes="panel", id="playlists-panel")
                yield SongsPanel(classes="panel", id="songs-panel")
                yield TagSchemaPanel(classes="panel", id="tags-panel")
            yield CommandPalette(id="command-palette")

    def on_mount(self) -> None:
        """Called when the app starts."""
        self.title = "Djroid - AI DJ Assistant"
        self.sub_title = "Rekordbox-inspired music management"

    def on_song_selected(self, event: SongSelected) -> None:
        """Handle song selection - highlight tags in schema panel."""
        try:
            tag_panel = self.query_one("#tags-panel")
            tag_panel.highlight_song_tags(event.song_data)
        except Exception:
            pass

    def on_song_tags_updated(self, event: SongTagsUpdated) -> None:
        """Handle song tags update - refresh yellow highlighting in songs panel."""
        try:
            songs_panel = self.query_one("#songs-panel")
            songs_panel.update_song_highlighting(event)
        except Exception:
            pass


def run_gui():
    """Entry point to run the GUI."""
    app = DjroidGUI()
    app.run()


if __name__ == "__main__":
    run_gui()
