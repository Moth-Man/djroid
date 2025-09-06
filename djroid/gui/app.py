from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Input, Tree, DataTable, Button
from textual.containers import ScrollableContainer
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from ..services.tag_schema import TagSchema


class ChatBox(Static):
    """Chat input box at the top of the application."""
    
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Chat with djroid...", id="chat-input")


class PlaylistPanel(Static):
    """Left panel showing playlist tree structure."""
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("📁 PLAYLISTS", classes="panel-header")
            tree = Tree("Root")
            tree.root.expand()
            
            # Add some sample playlists
            tree.root.add_leaf("🎵 House Classics")
            tree.root.add_leaf("🎶 Tech House")
            tree.root.add_leaf("🎧 Deep House")
            favorites = tree.root.add("⭐ Favorites")
            favorites.add_leaf("Top 100")
            favorites.add_leaf("Recent Finds")
            
            yield tree


class SongsPanel(Static):
    """Middle panel showing songs list."""
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("SONGS", classes="panel-header")
            table = DataTable()
            table.add_columns("Title", "Artist", "Genre", "BPM", "Key")
            
            # Add some sample songs
            table.add_row("Sweet Dreams", "Eurythmics", "Synth-pop", "132", "Cm")
            table.add_row("Blue Monday", "New Order", "Electronic", "125", "F#m")
            table.add_row("Strings of Life", "Derrick May", "Detroit Techno", "125", "Gm")
            
            yield table




class TagSchemaPanel(Static):
    """Right panel showing tag schema."""
    
    selected_category: reactive[str | None] = reactive(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tag_schema = TagSchema()
        self.schema_data = {}
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("TAG SCHEMA", classes="panel-header")
            table = DataTable(id="schema-table")
            table.cursor_type = "row"
            table.zebra_stripes = False
            yield table
    
    def on_mount(self) -> None:
        """Called when the widget is mounted to the DOM."""
        self.load_schema_data()
                
    def load_schema_data(self):
        """Load and display all schema data in flat table format"""
        try:
            self.schema_data = self.tag_schema.load_schema()
            table = self.query_one("#schema-table")
            table.clear(columns=True)
            
            # Show all categories and their values in one flat table - force full width
            table.add_column("Tag Schema", width=50)
            
            # Add blank first row
            table.add_row("")
            
            if not self.schema_data:
                table.add_row("No tag schema found")
                return
            
            category_count = len(self.schema_data)
            current_category = 0
            
            for category, values in self.schema_data.items():
                current_category += 1
                
                # Add category name in bold
                category_text = Text(category.title(), style="bold white")
                table.add_row(category_text)
                
                # Add all values for this category
                if isinstance(values, list):
                    for value in values:
                        table.add_row(f"  {value}")
                elif isinstance(values, dict) and values.get("type") == "rating":
                    max_rating = values.get("max_rating", 5)
                    for i in range(1, max_rating + 1):
                        table.add_row(f"  {i}")
                
                # Add blank row after each category (except the last one)
                if current_category < category_count:
                    table.add_row("")
            
            # Refresh the table layout to ensure proper column sizing
            table.refresh()
        
        except Exception as e:
            # Add error message to table
            table = self.query_one("#schema-table")
            table.clear(columns=True)
            table.add_column("")
            table.add_row("")
            table.add_row(f"Error loading schema: {str(e)}")
    


class DjroidGUI(App):
    """Main Djroid GUI application."""
    
    CSS = """
    Screen {
        background: #0a0a0a;
        color: #e0e0e0;
    }
    
    #chat-container {
        height: 3;
        background: #1a1a1a;
        border: solid #333333;
        margin: 1;
    }
    
    #main-container {
        height: 1fr;
        background: #0f0f0f;
    }
    
    #chat-input {
        background: #1a1a1a;
        color: #e0e0e0;
        border: none;
    }
    
    .panel {
        border: solid #333333;
        margin: 1;
        background: #0a0a0a;
    }
    
    
    .panel-header {
        background: #2a2a2a;
        color: #ffffff;
        text-align: center;
        height: 3;
        content-align: center middle;
        text-style: bold;
    }
    
    #playlists-panel {
        width: 1fr;
    }
    
    #songs-panel {
        width: 2fr;
    }
    
    #tags-panel {
        width: 1fr;
    }
    
    Tree {
        background: #0a0a0a;
        color: #e0e0e0;
    }
    
    DataTable {
        background: #0a0a0a;
        color: #e0e0e0;
    }
    
    DataTable > .datatable--header {
        background: #2a2a2a;
        color: #e0e0e0;
        text-style: bold;
    }
    
    DataTable > .datatable--cursor {
        background: #1a1a1a;
    }
    
    /* Tag Schema Panel Specific Styles */
    #tags-panel DataTable {
        background: #0a0a0a;
        color: #e0e0e0;
        width: 100%;
    }
    
    #tags-panel DataTable > .datatable--header {
        background: #2a2a2a;
        color: #e0e0e0;
        text-style: bold;
    }
    
    #tags-panel DataTable > .datatable--cursor {
        background: #333333;
        color: #ffffff;
    }
    
    #tags-panel DataTable > .datatable--cursor:hover {
        background: #444444;
        color: #ffffff;
    }
    
    /* Custom zebra stripes since we disabled the built-in ones */
    #schema-table .datatable--row:odd {
        background: #111111;
    }
    
    #schema-table .datatable--row:even {
        background: #0a0a0a;
    }
    
    #schema-table .datatable--row:hover {
        background: #333333;
    }
    
    """
    
    def compose(self) -> ComposeResult:
        with Vertical():
            # Chat box at top
            with Container(id="chat-container"):
                yield ChatBox()
            
            # Main 3-column layout below
            with Horizontal(id="main-container"):
                yield PlaylistPanel(classes="panel", id="playlists-panel")
                yield SongsPanel(classes="panel", id="songs-panel") 
                yield TagSchemaPanel(classes="panel", id="tags-panel")
    
    def on_mount(self) -> None:
        """Called when the app starts."""
        self.title = "Djroid - AI DJ Assistant"
        self.sub_title = "Rekordbox-inspired music management"


def run_gui():
    """Entry point to run the GUI."""
    app = DjroidGUI()
    app.run()


if __name__ == "__main__":
    run_gui()