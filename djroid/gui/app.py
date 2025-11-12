from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Input, Tree, DataTable, Button, Sparkline
from textual.containers import ScrollableContainer
from textual.reactive import reactive
from textual.message import Message
from textual import events
from textual.scroll_view import ScrollView
from textual.events import MouseScrollDown, MouseScrollUp
from textual.widget import Widget
from rich.text import Text
from ..services.tag_schema import TagSchema
from ..services.tag import Tag
from ..db.session import SessionLocal
from ..db.dao.song_dao import SongDAO
from ..db.models.song import Song
from typing import Tuple, List
from pathlib import Path


class SongSelected(Message):
    """Message sent when a song is selected"""
    
    def __init__(self, song_data: dict) -> None:
        super().__init__()
        self.song_data = song_data


class TitleBar(Static):
    """Title bar at the very top of the application."""

    def compose(self) -> ComposeResult:
        yield Static("dj-en v1.0.0", id="app-title")


class NavigationHeader(Static):
    """Navigation header with tabs for different views."""

    def compose(self) -> ComposeResult:
        with Horizontal(id="nav-buttons"):
            yield Button("Library", id="btn-library", variant="primary")
            yield Button("Chat", id="btn-chat")
            yield Button("Settings", id="btn-settings")


class CommandPalette(Static):
    """Command palette footer showing available commands."""

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold #888888]^l[/] library   [bold #888888]^c[/] chat   "
            "[bold #888888]^s[/] settings   [bold #888888]^h[/] help   [bold #888888]^q[/] quit",
            id="command-palette-text"
        )


class SongsDataTable(DataTable):
    """Custom DataTable for songs that highlights rows with no tags."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.no_tags_row_keys = set()

    def render_line(self, y: int):
        """Render a line, applying warning styling to rows with no tags."""
        from rich.style import Style

        strip = super().render_line(y)

        # Only try to style if we have rows with no tags
        if not self.no_tags_row_keys:
            return strip

        try:
            # Get the row key for this line using the private method
            # This returns the RowKey for the row being rendered
            row_key, _ = self._get_offsets(y)
            row_key_str = str(row_key.value)

            # Check if this row key is in our no-tags set
            # Convert RowKey to string for comparison with string keys in the set
            if row_key_str in self.no_tags_row_keys:
                # Check if this is the currently highlighted/selected row
                # If so, let the default blue selection styling show through
                if self.cursor_row is not None:
                    # Get the row index from the row key to compare with cursor_row
                    row_index = list(self.rows.keys()).index(row_key) if row_key in self.rows else -1
                    if row_index == self.cursor_row:
                        # This row is selected, use default styling (blue highlight)
                        return strip

                # Apply warning styling like Posting's "read-only" button
                # Use warning colors similar to $warning-muted (background) and $text-warning (foreground)
                from rich.segment import Segment
                from textual.strip import Strip

                # Colors based on Textual's warning theme:
                # - Background: dark muted orange (similar to warning color with low opacity on dark bg)
                # - Text: bright warning orange for good contrast
                bg_color = "#3d2817"  # dark muted warning background ($warning-muted equivalent)
                text_color = "#ffb454"  # bright warning text ($text-warning equivalent)

                new_segments = [
                    Segment(seg.text, Style.from_meta(seg.style.meta if seg.style else {}) + Style(bgcolor=bg_color, color=text_color))
                    for seg in strip
                ]
                strip = Strip(new_segments)
        except (IndexError, AttributeError, ValueError, KeyError, LookupError) as e:
            # Silently ignore errors for header rows or invalid y coordinates
            pass

        return strip


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

            # Add some sample playlists
            tree.root.add_leaf("House Classics")
            tree.root.add_leaf("Tech House")
            tree.root.add_leaf("Deep House")
            favorites = tree.root.add("Favorites")
            favorites.add_leaf("Top 100")
            favorites.add_leaf("Recent Finds")

            yield tree


class SongsPanel(Static):
    """Middle panel showing songs list."""

    def on_mount(self) -> None:
        """Set the border title when mounted."""
        self.border_title = "Collection"
        # Call parent on_mount logic after setting border_title
        self._setup_songs()

    def _setup_songs(self) -> None:
        """Setup songs after mount."""
        self.current_page = 0
        self.total_songs = 0
        self.all_songs = []
        self.songs_per_page = 15  # Default, will be recalculated after mounting

        # Sort state tracking
        self.sort_column = None  # Current column being sorted
        self.sort_order = None  # "asc", "desc", or None for no sort

        # Column configuration: column_index -> (column_name, data_key, is_numeric)
        self.column_config = {
            0: ("Title", "title", False),
            1: ("Artist", "artist", False),
            2: ("Genre", "genre", False),
            3: ("BPM", "bpm", True),
            4: ("Key", "key", False),
            5: ("Quality", "quality_score", True),
        }

        self.calculate_songs_per_page()
        self.load_songs()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("SONGS", classes="panel-header")
            with Horizontal(id="songs-content"):
                # Main songs table with fixed height (no scrolling)
                with Vertical(id="table-container"):
                    table = SongsDataTable(id="songs-table")
                    table.cursor_type = "row"
                    table.zebra_stripes = True
                    yield table

                # Sparkline panel (fixed height, no scrolling)
                with Vertical(id="sparkline-panel"):
                    yield Static("Preview", classes="sparkline-header")
                    with Vertical(id="sparkline-content"):
                        pass  # Sparklines will be added dynamically

            # Pagination controls at bottom
            with Horizontal(id="pagination-controls"):
                yield Button("← Prev", id="btn-prev", classes="pagination-btn")
                yield Static(id="page-info", classes="page-info")
                yield Button("Next →", id="btn-next", classes="pagination-btn")

    def calculate_songs_per_page(self) -> None:
        """Calculate how many songs can fit based on available height"""
        try:
            if not self.is_mounted:
                return

            # Get the songs-content container which has the actual available space
            songs_content = self.query_one("#songs-content")

            # Calculate available height for songs
            # Panel height - header (3) - pagination controls (3)
            available_height = self.size.height - 6  # 3 for header + 3 for pagination

            # Each song row takes 1 line in the table
            # Account for the table header (1 line)
            available_for_rows = available_height - 1

            # Ensure we have at least 1 song per page
            self.songs_per_page = max(1, available_for_rows)
        except Exception:
            # Fall back to default if calculation fails
            self.songs_per_page = 15
    
    def load_songs(self):
        """Load all songs from database and display the current page"""
        try:
            # Get database session
            db = SessionLocal()

            # Query ALL songs to populate self.all_songs
            from djroid.db.models.song import Song
            songs = db.query(Song.id, Song.title, Song.artist, Song.genre, Song.bpm, Song.key, Song.tags, Song.filepath, Song.quality_score, Song.waveform_preview).all()

            # Store all songs in memory for pagination
            self.all_songs = []
            for song in songs:
                self.all_songs.append({
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

            # Keep a backup of original order for resetting sort
            self.original_songs = [song.copy() for song in self.all_songs]

            self.total_songs = len(self.all_songs)
            self.current_page = 0

            # Reset sorting to original order
            self.sort_column = None
            self.sort_order = None

            # Display the first page
            self.display_page()

        except Exception as e:
            # Add error message to table
            table = self.query_one("#songs-table")
            table.clear(columns=True)
            table.add_column("Error")
            table.add_row(f"Error loading songs: {str(e)}")

        finally:
            if 'db' in locals():
                db.close()

    def _check_song_has_tags(self, song: dict) -> bool:
        """Check if a song has any tags from the tag schema.

        A song is considered to have tags if the tags field is a non-empty dict
        with at least one category having values.
        Tags could be None, empty dict {}, or a populated dict.
        """
        tags = song.get('tags')

        # If tags is None or not a dict, it has no tags
        if tags is None or not isinstance(tags, dict):
            return False

        # If tags is an empty dict, it has no tags
        if len(tags) == 0:
            return False

        # Check if any of the tag values are non-empty
        # Tags dict structure: {"category": [...values...], ...}
        for category, value in tags.items():
            if value is not None:
                if isinstance(value, (list, str)) and len(value) > 0:
                    return True
                elif isinstance(value, dict) and value.get("type") == "rating":
                    # Rating category - check if a value is set
                    return True
                elif isinstance(value, (int, float)) and value > 0:
                    return True

        return False

    def display_page(self):
        """Display songs for the current page"""
        # Calculate pagination boundaries
        start_idx = self.current_page * self.songs_per_page
        end_idx = start_idx + self.songs_per_page
        page_songs = self.all_songs[start_idx:end_idx]

        # Clear table and sparklines
        table = self.query_one("#songs-table")
        table.clear(columns=True)
        table.no_tags_row_keys.clear()  # Clear the no-tags tracking

        # Add columns
        table.add_column("Title", width=30)
        table.add_column("Artist", width=25)
        table.add_column("Genre", width=18)
        table.add_column("BPM", width=8)
        table.add_column("Key", width=8)
        table.add_column("Quality", width=10)

        # Clear sparklines
        sparkline_content = self.query_one("#sparkline-content")
        sparkline_content.remove_children()

        # Store song data for this page
        self.song_data = []
        self.sparklines = []
        self.row_keys = []  # Track row keys for styling
        self.no_tags_row_keys = set()  # Track rows with no tags

        if not page_songs:
            table.add_row("No songs found", "", "", "", "", "")
            self.update_page_info()
            return

        # Add songs and sparklines
        for song in page_songs:
            # Format BPM
            bpm_str = ""
            if song['bpm']:
                try:
                    bpm_str = str(int(float(song['bpm'])))
                except (ValueError, TypeError):
                    bpm_str = str(song['bpm'])

            # Format quality score
            quality_str = ""
            if song['quality_score'] is not None:
                quality_str = f"{song['quality_score']:.2f}"

            # Store song data with page-relative index
            self.song_data.append(song)

            # Generate waveform data
            from math import sin
            waveform_data = song['waveform_preview'] or [abs(sin(x / 3.14)) for x in range(0, 360, 25)][:15]

            # Create sparkline with rotating color gradient
            song_index = len(self.song_data)
            gradient_patterns = [
                "gradient-1", "gradient-2", "gradient-3", "gradient-4", "gradient-5",
                "gradient-6", "gradient-7", "gradient-8", "gradient-9", "gradient-10"
            ]
            pattern_class = gradient_patterns[song_index % len(gradient_patterns)]

            sparkline = Sparkline(waveform_data, summary_function=max, classes=f"waveform-sparkline {pattern_class}")
            sparkline_content.mount(sparkline)
            self.sparklines.append(sparkline)

            # Add table row with page-relative index as key
            row_key = str(song_index - 1)
            self.row_keys.append((row_key, song))  # Store key and song data

            # Check if song has tags and track it
            has_tags = self._check_song_has_tags(song)

            if not has_tags:
                self.no_tags_row_keys.add(row_key)
                table.no_tags_row_keys.add(row_key)  # Add to table's tracking

            table.add_row(
                song['title'] or "Unknown",
                song['artist'] or "Unknown",
                song['genre'] or "",
                bpm_str,
                song['key'] or "",
                quality_str,
                key=row_key
            )

        # Refresh the table
        table.refresh()

        # Update pagination controls
        self.update_page_info()

    def update_page_info(self):
        """Update the page info display and enable/disable buttons"""
        page_info = self.query_one("#page-info")
        start_song = self.current_page * self.songs_per_page + 1
        end_song = min((self.current_page + 1) * self.songs_per_page, self.total_songs)
        page_info.update(f"[{start_song}-{end_song} of {self.total_songs}]")

        # Update button states
        prev_btn = self.query_one("#btn-prev")
        next_btn = self.query_one("#btn-next")

        prev_btn.disabled = self.current_page == 0
        next_btn.disabled = end_song >= self.total_songs

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle pagination button presses"""
        if event.button.id == "btn-prev":
            if self.current_page > 0:
                self.current_page -= 1
                self.display_page()
        elif event.button.id == "btn-next":
            max_page = (self.total_songs - 1) // self.songs_per_page
            if self.current_page < max_page:
                self.current_page += 1
                self.display_page()

    def on_resize(self) -> None:
        """Handle window resize events"""
        old_songs_per_page = self.songs_per_page
        self.calculate_songs_per_page()

        # If the number of songs per page changed, recalculate pagination
        if old_songs_per_page != self.songs_per_page and hasattr(self, 'all_songs') and self.all_songs:
            # Check if current page is still valid
            max_page = (self.total_songs - 1) // self.songs_per_page
            if self.current_page > max_page:
                self.current_page = max(0, max_page)

            self.display_page()
    
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
                    
                # Sync sparklines with table viewport
                self.sync_sparklines_with_table()
            except (IndexError, ValueError, AttributeError):
                pass
    
    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Handle column header clicks for sorting"""
        try:
            column_index = event.column_index
            if column_index not in self.column_config:
                return

            _, data_key, is_numeric = self.column_config[column_index]

            # Determine the new sort order
            if self.sort_column == column_index:
                # Same column clicked again - cycle through sort states
                if self.sort_order == "asc":
                    self.sort_order = "desc"
                elif self.sort_order == "desc":
                    # Third click - remove sorting
                    self.sort_column = None
                    self.sort_order = None
                else:
                    self.sort_order = "asc"
            else:
                # New column clicked - start with ascending
                self.sort_column = column_index
                if is_numeric:
                    self.sort_order = "asc"
                else:
                    self.sort_order = "asc"  # Alphabetical is ascending

            # Apply the sort to all_songs
            self.apply_sort()

            # Reset to first page and display
            self.current_page = 0
            self.display_page()

        except Exception as e:
            pass

    def apply_sort(self) -> None:
        """Apply current sort settings to all_songs"""
        # If no sort, restore original order
        if self.sort_column is None or self.sort_order is None:
            if hasattr(self, 'original_songs'):
                self.all_songs = [song.copy() for song in self.original_songs]
            return

        _, data_key, is_numeric = self.column_config[self.sort_column]

        try:
            if is_numeric:
                # Sort numeric columns
                self.all_songs.sort(
                    key=lambda x: (x[data_key] is None, x[data_key] if x[data_key] is not None else 0),
                    reverse=(self.sort_order == "desc")
                )
            else:
                # Sort string columns alphabetically
                self.all_songs.sort(
                    key=lambda x: (x[data_key] is None, str(x[data_key] or "").lower()),
                    reverse=(self.sort_order == "desc")
                )
        except Exception:
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
        self.tag_service = Tag()
        self.schema_data = {}
        self.current_song = None
    
    def compose(self) -> ComposeResult:
        with Vertical():
            table = DataTable(id="schema-table")
            table.cursor_type = "row"
            table.zebra_stripes = True
            yield table
    
    def on_mount(self) -> None:
        """Called when the widget is mounted to the DOM."""
        self.border_title = "Tag Schema"
        self.load_schema_data()
                
    def load_schema_data(self, highlighted_tags=None):
        """Load and display all schema data in flat table format with optional highlighting"""
        try:
            self.schema_data = self.tag_schema.load_schema()
            table = self.query_one("#schema-table")
            table.clear(columns=True)

            # Show all categories and their values in one flat table - force full width
            table.add_column("", width=50)

            # Add blank first row
            table.add_row("", key="blank_start")

            if not self.schema_data:
                table.add_row("No tag schema found")
                return

            category_count = len(self.schema_data)
            current_category = 0

            for category, values in self.schema_data.items():
                current_category += 1

                # Add category name in bold
                category_text = Text(category.title(), style="bold white")
                table.add_row(category_text, key=f"category_{category}")

                # Add all values for this category
                if isinstance(values, list):
                    # Sort values alphabetically
                    sorted_values = sorted(values)
                    for value in sorted_values:
                        # Check if this value should be highlighted
                        if highlighted_tags and category in highlighted_tags:
                            song_values = highlighted_tags[category]
                            if isinstance(song_values, list) and value in song_values:
                                # Add checkmark and highlight in green
                                value_text = Text(f"✓ {value}", style="bold green")
                                table.add_row(value_text, key=f"tag_{category}_{value}")
                            else:
                                table.add_row(f"  {value}", key=f"tag_{category}_{value}")
                        else:
                            table.add_row(f"  {value}", key=f"tag_{category}_{value}")
                elif isinstance(values, dict) and values.get("type") == "rating":
                    max_rating = values.get("max_rating", 5)
                    for i in range(1, max_rating + 1):
                        # Check if this rating should be highlighted
                        if highlighted_tags and category in highlighted_tags:
                            song_rating = highlighted_tags[category]
                            if isinstance(song_rating, (int, float)) and int(song_rating) == i:
                                # Add checkmark and highlight in green
                                rating_text = Text(f"✓ {i}", style="bold green")
                                table.add_row(rating_text, key=f"rating_{category}_{i}")
                            else:
                                table.add_row(f"  {i}", key=f"rating_{category}_{i}")
                        else:
                            table.add_row(f"  {i}", key=f"rating_{category}_{i}")

                # Add blank row after each category (except the last one)
                if current_category < category_count:
                    table.add_row("", key=f"blank_{category}")

            # Refresh the table layout to ensure proper column sizing
            table.refresh()

        except Exception as e:
            # Add error message to table
            table = self.query_one("#schema-table")
            table.clear(columns=True)
            table.add_column("")
            table.add_row("")
            table.add_row(f"Error loading schema: {str(e)}")
    
    def highlight_song_tags(self, song_data):
        """Highlight tags in the schema that match the selected song"""
        self.current_song = song_data
        if song_data and song_data.get('tags'):
            self.load_schema_data(song_data['tags'])
        else:
            self.load_schema_data()

    def on_data_table_row_selected(self, event) -> None:
        """Handle tag selection in the schema table"""
        if event.data_table.id == "schema-table" and self.current_song:
            try:
                # Parse the row key to get category and value
                row_key = event.row_key.value

                # Skip blank rows and category headers
                if row_key.startswith("blank_") or row_key.startswith("category_"):
                    return

                # Handle tag values
                if row_key.startswith("tag_"):
                    # Extract category and value from key like "tag_category_value"
                    parts = row_key.split("_", 2)
                    if len(parts) >= 3:
                        category = parts[1]
                        value = parts[2]
                        self.toggle_tag(category, value)

                # Handle rating values
                elif row_key.startswith("rating_"):
                    # Extract category and rating from key like "rating_category_5"
                    parts = row_key.split("_", 2)
                    if len(parts) >= 3:
                        category = parts[1]
                        rating = parts[2]
                        self.set_rating(category, rating)

            except Exception as e:
                pass  # Silently handle errors

    def toggle_tag(self, category: str, value: str):
        """Toggle a tag value for the current song"""
        if not self.current_song:
            return

        try:
            file_path = Path(self.current_song['filepath'])
            current_tags = self.current_song.get('tags', {})

            # Check if the tag is currently set
            is_currently_set = False
            if category in current_tags:
                song_values = current_tags[category]
                if isinstance(song_values, list) and value in song_values:
                    is_currently_set = True

            if is_currently_set:
                # Remove the tag
                success = self.tag_service.remove_tag_from_file(file_path, category, value)
            else:
                # Add the tag
                success = self.tag_service.add_tag_to_file(file_path, category, value)

            if success:
                # Update the database
                self.update_song_tags_in_database()

        except Exception as e:
            pass  # Silently handle errors

    def set_rating(self, category: str, rating: str):
        """Set a rating value for the current song"""
        if not self.current_song:
            return

        try:
            file_path = Path(self.current_song['filepath'])

            # Use the rating method from tag service
            success = self.tag_service.set_rating_value(file_path, category, rating)

            if success:
                # Update the database
                self.update_song_tags_in_database()

        except Exception as e:
            pass  # Silently handle errors

    def update_song_tags_in_database(self):
        """Update the song's tags in the database after file modification"""
        if not self.current_song:
            return

        try:
            file_path = Path(self.current_song['filepath'])

            # Build new tags JSON from the file
            new_tags = self.tag_service.build_tags_json_from_file(file_path)

            # Update the database
            db = SessionLocal()
            try:
                song = db.query(Song).filter(Song.id == self.current_song['id']).first()
                if song:
                    song.tags = new_tags
                    db.commit()

                    # Update the current song data
                    self.current_song['tags'] = new_tags

                    # Refresh the display
                    self.highlight_song_tags(self.current_song)

            finally:
                db.close()

        except Exception as e:
            pass  # Silently handle errors
    


class DjroidGUI(App):
    """Main Djroid GUI application."""

    CSS = """
    * {
        scrollbar-color: #555555 10%;
        scrollbar-color-hover: #777777 80%;
        scrollbar-color-active: #888888;
        scrollbar-background: #1a1a1a;
        scrollbar-background-hover: #1a1a1a;
        scrollbar-background-active: #1a1a1a;
        scrollbar-size-vertical: 1;
    }

    Screen {
        background: #0a0a0a;
        color: #cccccc;
    }

    #title-bar {
        width: 100%;
        height: auto;
        background: #0f0f0f;
        border-bottom: solid #1a1a1a;
        padding: 0;
        margin: 0;
    }

    #app-title {
        width: 100%;
        height: auto;
        background: #0f0f0f;
        color: #555555;
        text-align: left;
        padding: 0 1;
        content-align: left middle;
        border: none;
    }

    #nav-header {
        height: auto;
        background: #0a0a0a;
        border-bottom: solid #1a1a1a;
        margin: 0;
        padding: 0 1;
        align: left middle;
        content-align: left middle;
    }

    #nav-buttons {
        width: auto;
        height: 1;
        align: left middle;
    }

    #nav-buttons Button {
        margin: 0 2;
        background: transparent;
        color: #888888;
        border: none;
        &:hover {
            background: transparent;
            color: #aaaaaa;
        }
        &:focus {
            background: #1a1a1a;
            color: #cccccc;
            border: none;
        }
    }

    #command-palette {
        height: auto;
        background: #0f0f0f;
        border-top: solid #1a1a1a;
        margin: 0;
        padding: 0 1;
        align: center middle;
        content-align: center middle;
    }

    #command-palette-text {
        width: 100%;
        height: auto;
        align: center middle;
        content-align: center middle;
        color: #888888;
        background: transparent;
    }

    #main-container {
        height: 1fr;
        background: #0a0a0a;
        margin: 0;
        padding: 0;
    }

    .panel {
        border: solid #2a2a2a;
        border-title-color: #4a4a4a;
        border-title-align: left;
        margin: 0;
        padding: 0;
        background: #0a0a0a;
        height: 1fr;
        &:focus {
            border: solid #3a3a3a 100%;
            border-title-color: #666666;
            border-title-style: b;
        }
    }

    .panel-header {
        display: none;
    }

    #playlists-panel {
        width: 0.8fr;
        min-width: 24;
        height: 1fr;
        border-right: solid #2a2a2a;
    }

    #songs-panel {
        width: 2.6fr;
        min-width: 60;
        height: 1fr;
        border-right: solid #2a2a2a;
    }

    #tags-panel {
        width: 0.6fr;
        min-width: 22;
        height: 1fr;
    }

    Tree {
        background: #0a0a0a 50%;
        color: #cccccc;
        &:focus {
            outline: vkey #3a3a3a;
        }
    }

    DataTable {
        background: #0a0a0a;
        color: #cccccc;
        height: auto;
        width: 1fr;
        padding: 0 1;
        &:focus {
            width: 1fr;
            padding: 0;
            border-left: inner #3a3a3a;
        }
    }

    DataTable > .datatable--header {
        background: #1a1a1a;
        color: #777777;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #1a1a1a;
        color: #cccccc;
    }

    DataTable:blur > .datatable--cursor {
        background: transparent;
    }

    /* Cursor row styling - blue/green background with bold text */
    #songs-table > .datatable--cursor {
        background: $success-muted !important;
        color: $text-success !important;
        text-style: bold !important;
    }

    /* Target all text in cursor row */
    #songs-table .datatable--cursor {
        color: $text-success !important;
        text-style: bold !important;
    }

    /* Target cells within cursor row */
    #songs-table .datatable--cursor .datatable--cell {
        color: $text-success !important;
        text-style: bold !important;
    }

    /* Target any text content in cursor */
    #songs-table .datatable--cursor * {
        color: $text-success !important;
        text-style: bold !important;
    }

    /* Tag Schema Panel Specific Styles */
    #tags-panel DataTable {
        background: #0a0a0a;
        color: #aaaaaa;
        width: 100%;
        padding: 0;
        margin: 0;
    }

    #tags-panel DataTable > .datatable--header {
        background: #1a1a1a;
        color: #777777;
        text-style: bold;
    }

    #tags-panel DataTable > .datatable--cursor {
        background: #2a2a2a;
        color: #cccccc;
        margin: 0;
        padding: 0;
    }

    #tags-panel DataTable > .datatable--cursor:hover {
        background: #3a3a3a;
        color: #eeeeee;
    }

    /* Override built-in zebra stripes with our colors */
    #schema-table > .datatable--row-odd {
        background: #0f0f0f;
    }

    #schema-table > .datatable--row-even {
        background: #0a0a0a;
    }

    /* Ensure hover works on both zebra stripe types */
    #schema-table > .datatable--row:hover,
    #schema-table > .datatable--row-odd:hover,
    #schema-table > .datatable--row-even:hover {
        background: #2a2a2a !important;
        color: #cccccc !important;
    }

    /* Make clickable tag rows more obvious - removed cursor since Textual doesn't support it */

    /* Style for selected/active tags */
    #schema-table .tag-selected {
        color: #dddddd !important;
        text-style: bold;
    }

    /* Style for unselected tags */
    #schema-table .tag-unselected {
        color: #aaaaaa;
    }

    /* Hover effect for tag values specifically */
    #schema-table > .datatable--row:hover .tag-unselected,
    #schema-table > .datatable--row:hover .tag-selected {
        background: #3a3a3a;
    }
    
    /* Songs panel layout */
    #table-container {
        height: 1fr;
        width: 4fr;
    }
    
    #songs-table {
        height: 1fr;
        width: 100%;
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
        /* Use fractional units for responsive split */
        width: 4fr;
        height: 1fr;
        min-width: 70;
        max-width: 100%;
    }
    
    #sparkline-panel {
        width: 1fr;
        height: 1fr;
        min-width: 18;
        border-left: solid #2a2a2a;
    }

    #sparkline-content {
        width: 100%;
        height: auto;
    }

    .sparkline-header {
        background: #1a1a1a;
        color: #777777;
        text-align: center;
        height: 1;
        padding: 0;
        margin: 0;
        content-align: center middle;
        text-style: bold;
        border: none;
    }

    #sparkline-content {
        background: #0a0a0a;
        height: auto;
        padding: 0;
        margin: 0;
        overflow: hidden;
    }
    
    /* ============ WAVEFORM SPARKLINE STYLING ============ */
    .waveform-sparkline {
        width: 100%;
        height: 1;
        margin: 0;
        padding: 0;
        border: none;
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

    /* ============ PAGINATION CONTROLS ============ */
    #pagination-controls {
        height: 3;
        background: #1a1a1a;
        border-top: solid #2a2a2a;
        padding: 0 1;
        margin: 0;
        align: center middle;
        content-align: center middle;
    }

    Button {
        width: auto;
        margin: 0 1;
        padding: 0 1;
        background: #2a2a2a;
        color: #888888;
        border: none;
        text-style: bold;
        &:hover {
            background: #3a3a3a;
            color: #aaaaaa;
        }
        &:focus {
            background: #3a3a3a;
            color: #cccccc;
        }
        &:disabled {
            background: #0f0f0f;
            color: #444444;
            opacity: 40%;
        }
    }

    #page-info {
        width: 1fr;
        align: center middle;
        content-align: center middle;
        background: #1a1a1a;
        color: #777777;
        text-style: bold;
        margin: 0;
        padding: 0;
    }

    """
    
    def compose(self) -> ComposeResult:
        with Vertical():
            # Title bar at very top
            yield TitleBar(id="title-bar")

            # Navigation header
            yield NavigationHeader(id="nav-header")

            # Main 3-column layout
            with Horizontal(id="main-container"):
                yield PlaylistPanel(classes="panel", id="playlists-panel")
                yield SongsPanel(classes="panel", id="songs-panel")
                yield TagSchemaPanel(classes="panel", id="tags-panel")

            # Command palette at bottom
            yield CommandPalette(id="command-palette")
    
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
            tag_panel.highlight_song_tags(event.song_data)

        except Exception as e:
            pass  # Silently handle any errors


def run_gui():
    """Entry point to run the GUI."""
    app = DjroidGUI()
    app.run()


if __name__ == "__main__":
    run_gui()