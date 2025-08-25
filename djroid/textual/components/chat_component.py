"""
Chat interface component for the Djroid main window.
Handles command selection, navigation, and contextual information display.
"""

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Vertical
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

from ..config import COMMAND_COLORS, COMMAND_DESCRIPTIONS


class ChatComponent(Widget):
    """Main chat interface showing commands and djroid responses."""
    
    # Reactive attributes
    selected_command = reactive(0)
    commands = ["djtag", "djschema", "djscan", "djcrate"]
    
    def compose(self) -> ComposeResult:
        """Compose the chat interface."""
        with Vertical():
            yield Static(
                Panel(
                    Text("Welcome to DJROID", style="bold white", justify="center"),
                    title="HAL 9000 Interface",
                    border_style="blue",
                    padding=(1, 2)
                ),
                id="welcome_panel"
            )
            
            yield Static("", id="command_display")
            yield Static("", id="djroid_response")
            yield Static("", id="help_text")
        
    def on_mount(self) -> None:
        """Initialize the display when component mounts."""
        self.update_display()
        
    def update_display(self) -> None:
        """Update the command display and djroid response."""
        self.update_commands()
        self.update_djroid_response()
        self.update_help_text()
        
    def update_commands(self) -> None:
        """Update the command list display."""
        command_display = self.query_one("#command_display", Static)
        
        command_text = Text()
        command_text.append("Available Commands:\n\n", style="bold cyan")
        
        for i, command in enumerate(self.commands):
            prefix = "▶ " if i == self.selected_command else "  "
            
            # Define the color progression directly
            colors = ["red", "#d65d0e", "yellow", "green"]  # red -> orange -> yellow -> green
            color = colors[i] if i < len(colors) else "white"
            
            style = f"bold {color}" if i == self.selected_command else color
            
            command_text.append(f"{prefix}{command}", style=style)
            command_text.append("\n")
        
        command_panel = Panel(
            command_text,
            title="Commands",
            border_style="green",
            padding=(1, 2)
        )
        
        command_display.update(command_panel)
        
    def update_djroid_response(self) -> None:
        """Update djroid's contextual response."""
        djroid_response = self.query_one("#djroid_response", Static)
        
        current_command = self.commands[self.selected_command]
        description = COMMAND_DESCRIPTIONS.get(current_command, "Unknown command")
        
        response_text = Text()
        response_text.append("DJROID: ", style="bold red")
        response_text.append(description, style="white")
        
        response_panel = Panel(
            response_text,
            title="System Response",
            border_style="red", 
            padding=(1, 1)
        )
        
        djroid_response.update(response_panel)
        
    def update_help_text(self) -> None:
        """Update the help text at the bottom."""
        help_text = self.query_one("#help_text", Static)
        
        help_content = Text()
        help_content.append("Navigation: ", style="bold yellow")
        help_content.append("↑/↓ Select • Enter Execute • ` Toggle HAL • ESC/Q Quit", style="cyan")
        
        help_panel = Panel(
            help_content,
            border_style="yellow",
            padding=(0, 1)
        )
        
        help_text.update(help_panel)
        
    def move_selection(self, direction: int) -> None:
        """Move the command selection up or down."""
        new_selection = self.selected_command + direction
        
        # Wrap around the selection
        if new_selection < 0:
            new_selection = len(self.commands) - 1
        elif new_selection >= len(self.commands):
            new_selection = 0
            
        self.selected_command = new_selection
        self.update_display()
        
    def get_selected_command(self) -> str:
        """Get the currently selected command."""
        return self.commands[self.selected_command]
        
    def watch_selected_command(self, selected_command: int) -> None:
        """React to selection changes."""
        self.update_display()