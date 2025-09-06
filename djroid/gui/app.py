from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Input, Tree, DataTable, Button, Sparkline
from textual.containers import ScrollableContainer
from textual.reactive import reactive
from textual.message import Message
from textual import events
from rich.text import Text
from ..services.tag_schema import TagSchema
from ..db.session import SessionLocal
from ..db.dao.song_dao import SongDAO
from typing import Tuple, List


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
            yield Static("📁 PLAYLISTSSSSS", classes="panel-header")
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
                with Horizontal(id="songs-content"):
                    # Main songs table without Preview column
                    table = DataTable(id="songs-table")
                    table.cursor_type = "row"
                    table.zebra_stripes = True
                    yield table
                    
                    # Sparkline panel aligned with table rows
                    with Vertical(id="sparkline-panel"):
                        yield Static("Preview", classes="sparkline-header")
                        with Vertical(id="sparkline-container"):
                            pass  # Sparklines will be added dynamically
    
    def on_mount(self) -> None:
        """Called when the widget is mounted to the DOM."""
        self.load_songs()
    
    def load_songs(self):
        """Load and display songs from the database"""
        try:
            # Get database session
            db = SessionLocal()
            
            # Query songs with all fields we need including ID, tags, and audio analysis
            from djroid.db.models.song import Song
            songs = db.query(Song.id, Song.title, Song.artist, Song.genre, Song.bpm, Song.key, Song.tags, Song.filepath, Song.quality_score, Song.waveform_preview).limit(50).all()
            
            table = self.query_one("#songs-table")
            table.clear(columns=True)
            
            # Add columns with specific widths for better display
            table.add_column("Title", width=25)
            table.add_column("Artist", width=20) 
            table.add_column("Genre", width=15)
            table.add_column("BPM", width=6)
            table.add_column("Key", width=6)
            table.add_column("Quality", width=8)
            table.add_column("Preview", width=20)
            
            if not songs:
                table.add_row("No songs found", "", "", "", "", "", "")
                return
            
            # Store song data for click handling
            self.song_data = []
            
            # Clear and prepare sparkline container
            sparkline_container = self.query_one("#sparkline-container")
            sparkline_container.remove_children()
            
            # Add song rows and sparklines
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
                    'filepath': song.filepath,
                    'quality_score': song.quality_score,
                    'waveform_preview': song.waveform_preview
                })
                
                # Format quality score
                quality_str = ""
                if song.quality_score is not None:
                    quality_str = f"{song.quality_score:.2f}"
                
                # Create sparkline for separate panel
                # If no quality score, generate a varied one based on song index for demo
                quality_score = song.quality_score
                if quality_score is None:
                    # Create varied quality scores for demo (cycle through ranges)
                    song_index = len(self.song_data)
                    if song_index % 3 == 0:
                        quality_score = 0.9  # High quality
                    elif song_index % 3 == 1:
                        quality_score = 0.7  # Medium quality  
                    else:
                        quality_score = 0.4  # Low quality
                
                # Generate waveform data like the example
                from math import sin
                waveform_data = song.waveform_preview or [abs(sin(x / 3.14)) for x in range(0, 360, 25)][:15]
                
                # Create single sparkline with gradient colors
                # Use the current song index (before adding to song_data)
                song_index = len(self.song_data)
                
                # Cycle through different gradient patterns
                gradient_patterns = [
                    "gradient-1", "gradient-2", "gradient-3", "gradient-4", "gradient-5",
                    "gradient-6", "gradient-7", "gradient-8", "gradient-9", "gradient-10"
                ]
                pattern_class = gradient_patterns[song_index % len(gradient_patterns)]
                
                # Create sparkline with gradient class for separate panel
                sparkline = Sparkline(waveform_data, summary_function=max, classes=f"waveform-sparkline {pattern_class}")
                sparkline_container.mount(sparkline)
                
                # Create text-based preview for DataTable column
                preview_text = Text()
                for i, value in enumerate(waveform_data[:10]):  # Limit to 10 points for table
                    if value <= 0.3:
                        bar = "▁"
                    elif value <= 0.6:
                        bar = "▅"
                    else:
                        bar = "█"
                    
                    # Use gradient color based on pattern
                    color = "green" if pattern_class in ["gradient-6", "gradient-7", "gradient-8", "gradient-9"] else \
                            "yellow" if pattern_class in ["gradient-4", "gradient-5", "gradient-10"] else "red"
                    
                    preview_text.append(bar, style=color)
                
                table.add_row(
                    song.title or "Unknown",
                    song.artist or "Unknown", 
                    song.genre or "",
                    bpm_str,
                    song.key or "",
                    quality_str,
                    preview_text,
                    key=str(len(self.song_data) - 1)  # Use index as row key
                )
            
            # Refresh the table layout
            table.refresh()
        
        except Exception as e:
            # Add error message to table
            table = self.query_one("#songs-table")
            table.clear(columns=True)
            table.add_column("Error")
            table.add_row(f"Error loading songs: {str(e)}")
        
        finally:
            if 'db' in locals():
                db.close()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle song row selection (click)"""
        if event.data_table.id == "songs-table" and hasattr(self, 'song_data'):
            try:
                # Get the selected song data using the row key
                row_index = int(event.row_key.value)
                selected_song = self.song_data[row_index]
                
                # Send message to the app to highlight tags
                self.post_message(SongSelected(selected_song))
            except (IndexError, ValueError, AttributeError):
                pass
    
    def on_data_table_cursor_changed(self, event: events.CursorPosition) -> None:
        """Handle cursor movement in the table (arrow keys)"""
        if event.data_table.id == "songs-table" and hasattr(self, 'song_data'):
            try:
                # Get the current cursor row
                row_index = event.cursor_row
                if 0 <= row_index < len(self.song_data):
                    selected_song = self.song_data[row_index]
                    
                    # Send message to the app to highlight tags
                    self.post_message(SongSelected(selected_song))
            except (IndexError, ValueError, AttributeError):
                pass
    
    def on_key(self, event) -> None:
        """Handle key events to catch arrow navigation"""
        if event.key in ["up", "down"] and hasattr(self, 'song_data'):
            # Get the current table
            try:
                table = self.query_one("#songs-table")
                cursor_row = table.cursor_row
                
                if 0 <= cursor_row < len(self.song_data):
                    selected_song = self.song_data[cursor_row]
                    self.post_message(SongSelected(selected_song))
            except Exception:
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
                                # Add checkmark and highlight in green
                                value_text = Text(f"✓ {value}", style="bold green")
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
                                # Add checkmark and highlight in green
                                rating_text = Text(f"✓ {i}", style="bold green")
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
        height: 1fr;
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
        color: #00ff00 !important;
    }
    
    /* Ensure highlighted row text is green in songs table */
    #songs-table > .datatable--cursor {
        background: #1a1a1a !important;
        color: #00ff00 !important;
    }
    
    /* Target all text in cursor row */
    #songs-table .datatable--cursor {
        color: #00ff00 !important;
    }
    
    /* Target cells within cursor row */  
    #songs-table .datatable--cursor .datatable--cell {
        color: #00ff00 !important;
    }
    
    /* Target any text content in cursor */
    #songs-table .datatable--cursor * {
        color: #00ff00 !important;
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
    
    /* Improve waveform spacing and prevent blob effect */
    DataTable > .datatable--row {
        height: 1;
        padding: 0;
        margin: 0;
    }
    
    /* ============ SPARKLINE PANEL LAYOUT ============ */
    #songs-content {
        width: 100%;
        height: 1fr;
    }
    
    #songs-table {
        width: 75%;
        height: 1fr;
    }
    
    #sparkline-panel {
        width: 25%;
        min-width: 20;
        height: 1fr;
        border-left: solid #333;
    }
    
    .sparkline-header {
        background: #2a2a2a;
        color: #ffffff;
        text-align: center;
        height: 3;
        content-align: center middle;
        text-style: bold;
    }
    
    #sparkline-container {
        background: #0a0a0a;
        height: 1fr;
        padding: 1;
    }
    
    /* ============ WAVEFORM SPARKLINE STYLING ============ */
    .waveform-sparkline {
        width: 100%;
        height: 3;
        margin: 1 0;
        padding: 0;
        border: solid #333;
    }
    
    /* ============ SPARKLINE COLOR GRADIENTS ============ */
    
    /* Red-Orange-Green Spectrum Gradients */
    .gradient-1 > .sparkline--max-color { color: $error; }
    .gradient-1 > .sparkline--min-color { color: $error 30%; }
    
    .gradient-2 > .sparkline--max-color { color: $error; }
    .gradient-2 > .sparkline--min-color { color: $warning; }
    
    .gradient-3 > .sparkline--max-color { color: $warning; }
    .gradient-3 > .sparkline--min-color { color: $error; }
    
    .gradient-4 > .sparkline--max-color { color: $warning; }
    .gradient-4 > .sparkline--min-color { color: $warning 30%; }
    
    .gradient-5 > .sparkline--max-color { color: $warning; }
    .gradient-5 > .sparkline--min-color { color: $success; }
    
    .gradient-6 > .sparkline--max-color { color: $success; }
    .gradient-6 > .sparkline--min-color { color: $warning; }
    
    .gradient-7 > .sparkline--max-color { color: $success; }
    .gradient-7 > .sparkline--min-color { color: $success 30%; }
    
    .gradient-8 > .sparkline--max-color { color: $success; }
    .gradient-8 > .sparkline--min-color { color: $success 60%; }
    
    .gradient-9 > .sparkline--max-color { color: $accent; }
    .gradient-9 > .sparkline--min-color { color: $primary; }
    
    .gradient-10 > .sparkline--max-color { color: $primary; }
    .gradient-10 > .sparkline--min-color { color: $accent; }
    
    /* Default fallback */
    .waveform-sparkline > .sparkline--max-color { color: $success; }
    .waveform-sparkline > .sparkline--min-color { color: $warning; }
    
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