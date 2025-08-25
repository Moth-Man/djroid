"""
Main Djroid Textual application.
HAL 9000-inspired interface for music library management.
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer
from textual.reactive import reactive
from textual.binding import Binding

from .components.hal_component import HALComponent
from .components.chat_component import ChatComponent
from .config import COLORS, LAYOUT, KEYBINDINGS


class DjroidApp(App):
    """Main Djroid application with HAL 9000 interface."""
    
    # App configuration
    TITLE = "DJROID - HAL 9000 Interface"
    AUTO_FOCUS = None
    
    CSS = """
    Screen {
        background: #282828;
        color: #ebdbb2;
    }
    
    Horizontal {
        height: 100%;
    }
    
    #chat_interface {
        width: 75%;
        height: 100%;
        border: solid #504945;
        background: #1d2021;
        padding: 1;
    }
    
    #hal_component {
        width: 25%;
        height: 100%;
        border: solid #458588;
        background: #000000;
        padding: 1;
    }
    
    .hal-frame {
        text-align: center;
        content-align: center middle;
        background: #000000;
        width: 100%;
        height: 100%;
        overflow: hidden;
    }
    """
    
    # Reactive attributes
    hal_visible = reactive(True)
    
    # Key bindings
    BINDINGS = [
        Binding("q,escape", "quit", "Quit"),
        Binding("`", "toggle_hal", "Toggle HAL"),
        Binding("up,k", "nav_up", "Up"),
        Binding("down,j", "nav_down", "Down"),
        Binding("enter", "select", "Select"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        with Horizontal():
            # Chat interface takes 4/5 of the width
            yield ChatComponent(id="chat_interface")
            # HAL component takes 1/5 of the width  
            yield HALComponent(id="hal_component")
        
        yield Footer()
        
    def on_mount(self) -> None:
        """Initialize the app when it mounts."""
        self.title = self.TITLE
        # Set initial focus to chat interface
        self.query_one("#chat_interface").focus()
        
    def action_quit(self) -> None:
        """Handle quit action."""
        self.exit()
        
    def action_toggle_hal(self) -> None:
        """Toggle HAL 9000 visibility."""
        hal_component = self.query_one("#hal_component", HALComponent)
        hal_component.toggle_visibility()
        
    def action_nav_up(self) -> None:
        """Navigate up in the command list."""
        chat_component = self.query_one("#chat_interface", ChatComponent)
        chat_component.move_selection(-1)
        
    def action_nav_down(self) -> None:
        """Navigate down in the command list."""
        chat_component = self.query_one("#chat_interface", ChatComponent)
        chat_component.move_selection(1)
        
    def action_select(self) -> None:
        """Select the current command."""
        chat_component = self.query_one("#chat_interface", ChatComponent)
        selected_command = chat_component.get_selected_command()
        
        # For now, just show which command was selected
        # Later we'll implement the specific command windows
        self.notify(f"Selected command: {selected_command}")


def main():
    """Main entry point for the Djroid textual interface."""
    app = DjroidApp()
    app.run()


if __name__ == "__main__":
    main()