"""Main DJ-EN GUI application."""

from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button

from .messages import SongSelected, SongTagsUpdated, SettingsCategorySelected, TabChanged
from .components.title_bar import TitleBar
from .panels.navigation import NavigationHeader
from .panels.command_palette import CommandPalette
from .panels.playlists import PlaylistPanel
from .panels.collection_panel import CollectionPanel
from .panels.tag_schema_panel import TagSchemaPanel
from .panels.settings_category_panel import SettingsCategoryPanel
from .panels.migrate_settings_panel import MigrateSettingsPanel


class DjEnGUI(App):
    """Main DJ-EN GUI application."""

    CSS_PATH = Path(__file__).parent / "styles" / "styles.tcss"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_tab = "library"
        self.current_settings_category = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield TitleBar(id="title-bar")
            yield NavigationHeader(id="nav-header")
            with Horizontal(id="main-container"):
                # Library view panels (shown by default)
                yield PlaylistPanel(classes="panel", id="playlists-panel")
                yield CollectionPanel(classes="panel", id="collection-panel")
                yield TagSchemaPanel(classes="panel", id="tags-panel")

                # Settings view panels (hidden by default)
                settings_cat = SettingsCategoryPanel(classes="panel", id="settings-category-panel")
                settings_cat.display = False
                yield settings_cat

                migrate_panel = MigrateSettingsPanel(classes="panel", id="migrate-settings-panel")
                migrate_panel.display = False
                yield migrate_panel

                # Placeholder panel for other settings
                placeholder = Static(
                    "Select a category from the left panel.",
                    classes="panel placeholder-panel",
                    id="settings-placeholder-panel"
                )
                placeholder.display = False
                yield placeholder

            yield CommandPalette(id="command-palette")

    def on_mount(self) -> None:
        """Called when the app starts."""
        self.title = "DJ-EN - AI DJ Assistant"
        self.sub_title = "Rekordbox-inspired music management"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle navigation button presses."""
        button_id = event.button.id

        if button_id == "btn-library":
            self.switch_to_library()
        elif button_id == "btn-settings":
            self.switch_to_settings()
        elif button_id == "btn-chat":
            # Chat not implemented yet
            pass

    def switch_to_library(self) -> None:
        """Switch to library view."""
        if self.current_tab == "library":
            return

        self.current_tab = "library"

        # Hide settings panels
        self.query_one("#settings-category-panel").display = False
        self.query_one("#migrate-settings-panel").display = False
        self.query_one("#settings-placeholder-panel").display = False

        # Show library panels
        self.query_one("#playlists-panel").display = True
        self.query_one("#collection-panel").display = True
        self.query_one("#tags-panel").display = True

        # Update button styles
        self._update_nav_buttons("library")

    def switch_to_settings(self) -> None:
        """Switch to settings view."""
        if self.current_tab == "settings":
            return

        self.current_tab = "settings"

        # Hide library panels
        self.query_one("#playlists-panel").display = False
        self.query_one("#collection-panel").display = False
        self.query_one("#tags-panel").display = False

        # Show settings category panel
        self.query_one("#settings-category-panel").display = True

        # Show the appropriate settings panel based on current category
        if self.current_settings_category == "migrate":
            self.query_one("#migrate-settings-panel").display = True
            self.query_one("#settings-placeholder-panel").display = False
        else:
            self.query_one("#migrate-settings-panel").display = False
            self.query_one("#settings-placeholder-panel").display = True

        # Update button styles
        self._update_nav_buttons("settings")

    def _update_nav_buttons(self, active_tab: str) -> None:
        """Update navigation button styles based on active tab."""
        try:
            library_btn = self.query_one("#btn-library", Button)
            settings_btn = self.query_one("#btn-settings", Button)
            chat_btn = self.query_one("#btn-chat", Button)

            library_btn.variant = "primary" if active_tab == "library" else "default"
            settings_btn.variant = "primary" if active_tab == "settings" else "default"
            chat_btn.variant = "primary" if active_tab == "chat" else "default"
        except Exception:
            pass

    def on_settings_category_selected(self, event: SettingsCategorySelected) -> None:
        """Handle settings category selection."""
        self.current_settings_category = event.category

        # Hide all settings content panels
        self.query_one("#migrate-settings-panel").display = False
        self.query_one("#settings-placeholder-panel").display = False

        # Show the appropriate panel
        if event.category == "migrate":
            migrate_panel = self.query_one("#migrate-settings-panel", MigrateSettingsPanel)
            migrate_panel.display = True
            migrate_panel.load_available_options()
            migrate_panel.load_rules()
        else:
            # Show placeholder for unimplemented settings
            placeholder = self.query_one("#settings-placeholder-panel")
            placeholder.display = True
            placeholder.update(f"{event.category.title()} settings - Coming soon")

    def on_song_selected(self, event: SongSelected) -> None:
        """Handle song selection - highlight tags in schema panel."""
        try:
            tag_panel = self.query_one("#tags-panel")
            tag_panel.highlight_song_tags(event.song_data)
        except Exception:
            pass

    def on_song_tags_updated(self, event: SongTagsUpdated) -> None:
        """Handle song tags update - refresh yellow highlighting in collection panel."""
        try:
            collection_panel = self.query_one("#collection-panel")
            collection_panel.update_song_highlighting(event)
        except Exception:
            pass


def run_gui():
    """Entry point to run the GUI."""
    app = DJ-ENGUI()
    app.run()


if __name__ == "__main__":
    run_gui()
