"""Settings category panel widget for the dj-en GUI."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, OptionList
from textual.widgets.option_list import Option

from ..messages import SettingsCategorySelected


class SettingsCategoryPanel(Static):
    """Left panel showing settings categories as a clean list."""

    def on_mount(self) -> None:
        """Set the border title when mounted."""
        self.border_title = "Settings"

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-category-container"):
            yield OptionList(
                Option("  Migrate", id="migrate"),
                Option("  Appearance", id="appearance"),
                Option("  Analysis", id="analysis"),
                Option("  Database", id="database"),
                id="settings-option-list"
            )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle category selection."""
        if event.option.id:
            self.post_message(SettingsCategorySelected(event.option.id))
