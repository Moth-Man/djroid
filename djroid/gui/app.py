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
            yield Static("🎵 SONGS", classes="panel-header")
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
            yield Static("🏷️  TAG SCHEMA", classes="panel-header")
            table = DataTable(id="schema-table", show_header=False)
            table.cursor_type = "row"
            table.zebra_stripes = True
            yield table
    
    def on_mount(self) -> None:
        """Called when the widget is mounted to the DOM."""
        self.load_schema_data()
                
    def load_schema_data(self):
        """Load and display schema data in table"""
        self.schema_data = self.tag_schema.load_schema()
        table = self.query_one("#schema-table")
        table.clear(columns=True)
        
        if self.selected_category is None:
            # Show all categories
            table.add_column("")
            for category, values in self.schema_data.items():
                table.add_row(category.title())
        else:
            # Show selected category values with category name as first row
            if self.selected_category in self.schema_data:
                table.add_column("")
                
                # Add category name as first row with return arrow and bold styling
                category_text = Text(f"← {self.selected_category.title()}", style="bold white")
                table.add_row(category_text)
                
                values = self.schema_data[self.selected_category]
                if isinstance(values, list):
                    for value in values:
                        table.add_row(value)
                elif isinstance(values, dict) and values.get("type") == "rating":
                    max_rating = values.get("max_rating", 5)
                    for i in range(1, max_rating + 1):
                        table.add_row(str(i))
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the table"""
        table = event.data_table
        if self.selected_category is None:
            # We're in category view, switch to selected category
            row_data = table.get_row_at(event.cursor_row)
            category_name = str(row_data[0])
            
            # Find the actual category key (case-insensitive match)
            for key in self.schema_data.keys():
                if key.title() == category_name:
                    self.selected_category = key
                    break
            
            self.load_schema_data()
        else:
            # We're in values view, go back to categories if clicked on first row (category header)
            if event.cursor_row == 0:
                self.selected_category = None
                self.load_schema_data()


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
    #schema-table {
        background: #0a0a0a;
        color: #e0e0e0;
    }
    
    #schema-table > .datatable--header {
        background: #2a2a2a;
        color: #e0e0e0;
        text-style: bold;
    }
    
    #schema-table > .datatable--cursor {
        background: #333333;
        color: #ffffff;
    }
    
    #schema-table > .datatable--cursor:hover {
        background: #444444;
        color: #ffffff;
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