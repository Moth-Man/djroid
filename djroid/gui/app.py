from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Input, Tree, DataTable, Button
from textual.containers import ScrollableContainer
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from ..services.tag_schema import TagSchema
from ..db.session import SessionLocal
from ..db.dao.song_dao import SongDAO


class SongSelected(Message):
    """Message sent when a song is selected"""
    
    def __init__(self, song_data: dict) -> None:
        super().__init__()
        self.song_data = song_data


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
            with ScrollableContainer(id="songs-scroll-container"):
                table = DataTable(id="songs-table")
                table.cursor_type = "row"
                table.zebra_stripes = True
                yield table
    
    def on_mount(self) -> None:
        """Called when the widget is mounted to the DOM."""
        self.load_songs()
    
    def load_songs(self):
        """Load and display songs from the database"""
        try:
            # Get database session
            db = SessionLocal()
            
            # Query songs with all fields we need including ID and tags
            from djroid.db.models.song import Song
            songs = db.query(Song.id, Song.title, Song.artist, Song.genre, Song.bpm, Song.key, Song.tags, Song.filepath).limit(50).all()
            
            table = self.query_one("#songs-table")
            table.clear(columns=True)
            
            # Add columns with specific widths for better display
            table.add_column("Title", width=30)
            table.add_column("Artist", width=25) 
            table.add_column("Genre", width=20)
            table.add_column("BPM", width=8)
            table.add_column("Key", width=8)
            
            if not songs:
                table.add_row("No songs found", "", "", "", "")
                return
            
            # Store song data for click handling
            self.song_data = []
            
            # Add song rows
            for song in songs:
                # Format BPM safely
                bpm_str = ""
                if song.bpm:
                    try:
                        bpm_str = str(int(float(song.bpm)))
                    except (ValueError, TypeError):
                        bpm_str = str(song.bpm)
                
                # Store full song data
                self.song_data.append({
                    'id': song.id,
                    'title': song.title,
                    'artist': song.artist,
                    'genre': song.genre,
                    'bpm': song.bpm,
                    'key': song.key,
                    'tags': song.tags,
                    'filepath': song.filepath
                })
                
                table.add_row(
                    song.title or "Unknown",
                    song.artist or "Unknown", 
                    song.genre or "",
                    bpm_str,
                    song.key or "",
                    key=str(len(self.song_data) - 1)  # Use index as row key
                )
            
            # Refresh the table layout
            table.refresh()
        
        except Exception as e:
            # Add error message to table
            table = self.query_one("#songs-table")
            table.clear(columns=True)
            table.add_columns("Error")
            table.add_row(f"Error loading songs: {str(e)}")
        
        finally:
            if 'db' in locals():
                db.close()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle song row selection"""
        if event.data_table.id == "songs-table" and hasattr(self, 'song_data'):
            try:
                # Get the selected song data using the row key
                row_index = int(event.row_key.value)
                selected_song = self.song_data[row_index]
                
                # Send message to the app to highlight tags
                self.post_message(SongSelected(selected_song))
            except (IndexError, ValueError, AttributeError):
                pass




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
            table.zebra_stripes = True
            yield table
    
    def on_mount(self) -> None:
        """Called when the widget is mounted to the DOM."""
        self.load_schema_data()
                
    def load_schema_data(self, highlighted_tags=None):
        """Load and display all schema data in flat table format with optional highlighting"""
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
                        # Check if this value should be highlighted
                        if highlighted_tags and category in highlighted_tags:
                            song_values = highlighted_tags[category]
                            if isinstance(song_values, list) and value in song_values:
                                # Highlight in green
                                value_text = Text(f"  {value}", style="bold green")
                                table.add_row(value_text)
                            else:
                                table.add_row(f"  {value}")
                        else:
                            table.add_row(f"  {value}")
                elif isinstance(values, dict) and values.get("type") == "rating":
                    max_rating = values.get("max_rating", 5)
                    for i in range(1, max_rating + 1):
                        # Check if this rating should be highlighted
                        if highlighted_tags and category in highlighted_tags:
                            song_rating = highlighted_tags[category]
                            if isinstance(song_rating, (int, float)) and int(song_rating) == i:
                                # Highlight in green
                                rating_text = Text(f"  {i}", style="bold green")
                                table.add_row(rating_text)
                            else:
                                table.add_row(f"  {i}")
                        else:
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
    
    def highlight_song_tags(self, song_tags):
        """Highlight tags in the schema that match the selected song"""
        if song_tags:
            self.load_schema_data(song_tags)
        else:
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
    #tags-panel DataTable {
        background: #0a0a0a;
        color: #e0e0e0;
        width: 100%;
        padding: 0;
        margin: 0;
    }
    
    #tags-panel DataTable > .datatable--header {
        background: #2a2a2a;
        color: #e0e0e0;
        text-style: bold;
    }
    
    #tags-panel DataTable > .datatable--cursor {
        background: #333333;
        color: #ffffff;
        margin: 0;
        padding: 0;
    }
    
    #tags-panel DataTable > .datatable--cursor:hover {
        background: #444444;
        color: #ffffff;
    }
    
    /* Override built-in zebra stripes with our colors */
    #schema-table > .datatable--row-odd {
        background: #111111;
    }
    
    #schema-table > .datatable--row-even {
        background: #0a0a0a;
    }
    
    /* Ensure hover works on both zebra stripe types */
    #schema-table > .datatable--row:hover,
    #schema-table > .datatable--row-odd:hover,
    #schema-table > .datatable--row-even:hover {
        background: #333333 !important;
    }
    
    /* Songs panel scrolling - hide scrollbars */
    #songs-scroll-container {
        overflow-x: auto;
        overflow-y: auto;
        scrollbar-size: 0 0;
    }
    
    #songs-table {
        min-width: 100%;
        scrollbar-size: 0 0;
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
    
    def on_song_selected(self, event: SongSelected) -> None:
        """Handle song selection - highlight tags in schema panel"""
        try:
            # Get the tag schema panel
            tag_panel = self.query_one("#tags-panel")
            
            # Highlight the tags from the selected song
            tag_panel.highlight_song_tags(event.song_data.get('tags'))
            
        except Exception as e:
            pass  # Silently handle any errors


def run_gui():
    """Entry point to run the GUI."""
    app = DjroidGUI()
    app.run()


if __name__ == "__main__":
    run_gui()