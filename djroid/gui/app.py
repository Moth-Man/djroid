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


# Highlight color aliases
class HighlightColors:
    """Color constants for row highlighting."""
    WARNING_BG = "#3d2817"
    WARNING_FG = "#ffb454"

    ERROR_BG = "#3d1a1a"
    ERROR_FG = "#ff6b6b"

    SUCCESS_BG = "#1a3d2a"
    SUCCESS_FG = "#5ffa7f"

    INFO_BG = "#1a2a3d"
    INFO_FG = "#5f9ffa"


class SongSelected(Message):
    """Message sent when a song is selected"""

    def __init__(self, song_data: dict) -> None:
        super().__init__()
        self.song_data = song_data


class SongTagsUpdated(Message):
    """Message sent when a song's tags are updated"""

    def __init__(self, song_id: int, has_tags: bool, new_tags: dict) -> None:
        super().__init__()
        self.song_id = song_id
        self.has_tags = has_tags
        self.new_tags = new_tags


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
        from rich.segment import Segment
        from textual.strip import Strip

        strip = super().render_line(y)

        if not self.no_tags_row_keys:
            return strip

        try:
            scroll_x, scroll_y = self.scroll_offset
            fixed_rows_height = self.header_height if self.show_header else 0
            adjusted_y = y
            if y >= fixed_rows_height:
                adjusted_y = y + scroll_y

            row_key, _ = self._get_offsets(adjusted_y)
            row_key_str = str(row_key.value)

            if row_key_str in self.no_tags_row_keys:
                if self.cursor_row is not None:
                    row_index = list(self.rows.keys()).index(row_key) if row_key in self.rows else -1
                    if row_index == self.cursor_row:
                        return strip

                new_segments = [
                    Segment(seg.text, Style.from_meta(seg.style.meta if seg.style else {}) + Style(bgcolor=HighlightColors.WARNING_BG, color=HighlightColors.WARNING_FG))
                    for seg in strip
                ]
                strip = Strip(new_segments)
        except (IndexError, AttributeError, ValueError, KeyError, LookupError):
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
        self._setup_songs()

    def _setup_songs(self) -> None:
        """Initialize songs panel state."""
        self.current_page = 0
        self.total_songs = 0
        self.all_songs = []
        self.songs_per_page = 15
        self.sort_column = None
        self.sort_order = None
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
                with Vertical(id="table-container"):
                    table = SongsDataTable(id="songs-table")
                    table.cursor_type = "row"
                    table.zebra_stripes = True
                    yield table
                with Vertical(id="sparkline-panel"):
                    yield Static("Preview", classes="sparkline-header")
                    with Vertical(id="sparkline-content"):
                        pass
            with Horizontal(id="pagination-controls"):
                yield Button("← Prev", id="btn-prev", classes="pagination-btn")
                yield Static(id="page-info", classes="page-info")
                yield Button("Next →", id="btn-next", classes="pagination-btn")

    def calculate_songs_per_page(self) -> None:
        """Calculate how many songs can fit based on available height."""
        try:
            if not self.is_mounted:
                return
            songs_content = self.query_one("#songs-content")
            available_height = self.size.height - 6
            available_for_rows = available_height - 1
            self.songs_per_page = max(1, available_for_rows)
        except Exception:
            self.songs_per_page = 15
    
    def load_songs(self):
        """Load all songs from database and display the current page."""
        try:
            db = SessionLocal()
            from djroid.db.models.song import Song
            songs = db.query(Song.id, Song.title, Song.artist, Song.genre, Song.bpm, Song.key, Song.tags, Song.filepath, Song.quality_score, Song.waveform_preview).all()

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

            self.original_songs = [song.copy() for song in self.all_songs]
            self.total_songs = len(self.all_songs)
            self.current_page = 0
            self.sort_column = None
            self.sort_order = None
            self.display_page()

        except Exception as e:
            table = self.query_one("#songs-table")
            table.clear(columns=True)
            table.add_column("Error")
            table.add_row(f"Error loading songs: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()

    def _check_song_has_tags(self, song: dict) -> bool:
        """Check if a song has any tags from the tag schema."""
        tags = song.get('tags')

        if tags is None or not isinstance(tags, dict) or len(tags) == 0:
            return False

        for category, value in tags.items():
            if value is not None:
                if isinstance(value, (list, str)) and len(value) > 0:
                    return True
                elif isinstance(value, dict) and value.get("type") == "rating":
                    return True
                elif isinstance(value, (int, float)) and value > 0:
                    return True

        return False

    def display_page(self):
        """Display songs for the current page."""
        start_idx = self.current_page * self.songs_per_page
        end_idx = start_idx + self.songs_per_page
        page_songs = self.all_songs[start_idx:end_idx]

        table = self.query_one("#songs-table")
        table.clear(columns=True)
        table.no_tags_row_keys.clear()

        table.add_column("Title", width=30)
        table.add_column("Artist", width=25)
        table.add_column("Genre", width=18)
        table.add_column("BPM", width=8)
        table.add_column("Key", width=8)
        table.add_column("Quality", width=10)

        sparkline_content = self.query_one("#sparkline-content")
        sparkline_content.remove_children()

        self.song_data = []
        self.sparklines = []
        self.row_keys = []
        self.no_tags_row_keys = set()

        if not page_songs:
            table.add_row("No songs found", "", "", "", "", "")
            self.update_page_info()
            return

        for song in page_songs:
            bpm_str = ""
            if song['bpm']:
                try:
                    bpm_str = str(int(float(song['bpm'])))
                except (ValueError, TypeError):
                    bpm_str = str(song['bpm'])

            quality_str = ""
            if song['quality_score'] is not None:
                quality_str = f"{song['quality_score']:.2f}"

            self.song_data.append(song)

            from math import sin
            waveform_data = song['waveform_preview'] or [abs(sin(x / 3.14)) for x in range(0, 360, 25)][:15]

            song_index = len(self.song_data)
            gradient_patterns = [
                "gradient-1", "gradient-2", "gradient-3", "gradient-4", "gradient-5",
                "gradient-6", "gradient-7", "gradient-8", "gradient-9", "gradient-10"
            ]
            pattern_class = gradient_patterns[song_index % len(gradient_patterns)]

            sparkline = Sparkline(waveform_data, summary_function=max, classes=f"waveform-sparkline {pattern_class}")
            sparkline_content.mount(sparkline)
            self.sparklines.append(sparkline)

            row_key = str(song_index - 1)
            self.row_keys.append((row_key, song))

            has_tags = self._check_song_has_tags(song)
            if not has_tags:
                self.no_tags_row_keys.add(row_key)
                table.no_tags_row_keys.add(row_key)

            table.add_row(
                song['title'] or "Unknown",
                song['artist'] or "Unknown",
                song['genre'] or "",
                bpm_str,
                song['key'] or "",
                quality_str,
                key=row_key
            )

        table.refresh()
        self.update_page_info()

    def update_page_info(self):
        """Update the page info display and enable/disable buttons."""
        page_info = self.query_one("#page-info")
        start_song = self.current_page * self.songs_per_page + 1
        end_song = min((self.current_page + 1) * self.songs_per_page, self.total_songs)
        page_info.update(f"[{start_song}-{end_song} of {self.total_songs}]")

        prev_btn = self.query_one("#btn-prev")
        next_btn = self.query_one("#btn-next")
        prev_btn.disabled = self.current_page == 0
        next_btn.disabled = end_song >= self.total_songs

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle pagination button presses."""
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
        """Handle window resize events."""
        old_songs_per_page = self.songs_per_page
        self.calculate_songs_per_page()

        if old_songs_per_page != self.songs_per_page and hasattr(self, 'all_songs') and self.all_songs:
            max_page = (self.total_songs - 1) // self.songs_per_page
            if self.current_page > max_page:
                self.current_page = max(0, max_page)
            self.display_page()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle song row selection (click)."""
        if event.data_table.id == "songs-table" and hasattr(self, 'song_data'):
            try:
                row_index = int(event.row_key.value)
                selected_song = self.song_data[row_index]
                self.post_message(SongSelected(selected_song))
            except (IndexError, ValueError, AttributeError):
                pass

    def on_data_table_cursor_changed(self, event: events.CursorPosition) -> None:
        """Handle cursor movement in the table (arrow keys)."""
        if event.data_table.id == "songs-table" and hasattr(self, 'song_data'):
            try:
                row_index = event.cursor_row
                if 0 <= row_index < len(self.song_data):
                    selected_song = self.song_data[row_index]
                    self.post_message(SongSelected(selected_song))
                self.sync_sparklines_with_table()
            except (IndexError, ValueError, AttributeError):
                pass
    
    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Handle column header clicks for sorting."""
        try:
            column_index = event.column_index
            if column_index not in self.column_config:
                return

            _, data_key, is_numeric = self.column_config[column_index]

            if self.sort_column == column_index:
                if self.sort_order == "asc":
                    self.sort_order = "desc"
                elif self.sort_order == "desc":
                    self.sort_column = None
                    self.sort_order = None
                else:
                    self.sort_order = "asc"
            else:
                self.sort_column = column_index
                self.sort_order = "asc"

            self.apply_sort()
            self.current_page = 0
            self.display_page()

        except Exception:
            pass

    def apply_sort(self) -> None:
        """Apply current sort settings to all_songs."""
        if self.sort_column is None or self.sort_order is None:
            if hasattr(self, 'original_songs'):
                self.all_songs = [song.copy() for song in self.original_songs]
            return

        _, data_key, is_numeric = self.column_config[self.sort_column]

        try:
            if is_numeric:
                self.all_songs.sort(
                    key=lambda x: (x[data_key] is None, x[data_key] if x[data_key] is not None else 0),
                    reverse=(self.sort_order == "desc")
                )
            else:
                self.all_songs.sort(
                    key=lambda x: (x[data_key] is None, str(x[data_key] or "").lower()),
                    reverse=(self.sort_order == "desc")
                )
        except Exception:
            pass

    def on_key(self, event) -> None:
        """Handle key events to catch arrow navigation."""
        if event.key in ["up", "down"] and hasattr(self, 'song_data'):
            try:
                table = self.query_one("#songs-table")
                cursor_row = table.cursor_row
                if 0 <= cursor_row < len(self.song_data):
                    selected_song = self.song_data[cursor_row]
                    self.post_message(SongSelected(selected_song))
            except Exception:
                pass

    def update_song_highlighting(self, event: SongTagsUpdated) -> None:
        """Handle updates to song tags to refresh yellow highlighting."""
        if not hasattr(self, 'song_data') or not hasattr(self, 'all_songs'):
            return

        table = self.query_one("#songs-table")

        for song in self.all_songs:
            if song['id'] == event.song_id:
                song['tags'] = event.new_tags
                break

        if hasattr(self, 'original_songs'):
            for song in self.original_songs:
                if song['id'] == event.song_id:
                    song['tags'] = event.new_tags
                    break

        for i, song in enumerate(self.song_data):
            if song['id'] == event.song_id:
                song['tags'] = event.new_tags
                row_key = str(i)

                if event.has_tags:
                    self.no_tags_row_keys.discard(row_key)
                    table.no_tags_row_keys.discard(row_key)
                else:
                    self.no_tags_row_keys.add(row_key)
                    table.no_tags_row_keys.add(row_key)

                table.refresh()
                break


class SchemaDataTable(DataTable):
    """Custom DataTable for tag schema that highlights selected tags with green and errors with red."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_tag_row_keys = set()
        self.error_row_keys = set()

    def update_selected_keys(self, keys: set):
        """Update the selected keys and force a full refresh."""
        self.selected_tag_row_keys = keys
        self.refresh(layout=True)

    def update_error_keys(self, keys: set):
        """Update the error keys and force a full refresh."""
        self.error_row_keys = keys
        self.refresh(layout=True)

    def render_line(self, y: int):
        """Render a line, applying green styling to selected tags or red styling to errors."""
        from rich.style import Style
        from rich.segment import Segment
        from textual.strip import Strip

        strip = super().render_line(y)

        if not self.selected_tag_row_keys and not self.error_row_keys:
            return strip

        try:
            scroll_x, scroll_y = self.scroll_offset
            fixed_rows_height = self.header_height if self.show_header else 0
            adjusted_y = y
            if y >= fixed_rows_height:
                adjusted_y = y + scroll_y

            row_key, _ = self._get_offsets(adjusted_y)
            if row_key is None:
                return strip

            row_key_str = str(row_key.value)

            bg_color = None
            text_color = None

            if row_key_str in self.error_row_keys:
                bg_color = HighlightColors.ERROR_BG
                text_color = HighlightColors.ERROR_FG
            elif row_key_str in self.selected_tag_row_keys:
                if self.cursor_row is not None:
                    try:
                        row_keys_list = list(self.rows.keys())
                        if row_key in row_keys_list:
                            row_index = row_keys_list.index(row_key)
                            if row_index == self.cursor_row:
                                return strip
                    except (ValueError, IndexError):
                        pass
                bg_color = HighlightColors.SUCCESS_BG
                text_color = HighlightColors.SUCCESS_FG

            if bg_color and text_color:
                new_segments = [
                    Segment(seg.text, Style.from_meta(seg.style.meta if seg.style else {}) + Style(bgcolor=bg_color, color=text_color))
                    for seg in strip
                ]
                strip = Strip(new_segments)
        except (IndexError, AttributeError, ValueError, KeyError, LookupError, TypeError):
            pass

        return strip


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
            table = SchemaDataTable(id="schema-table")
            table.cursor_type = "row"
            table.zebra_stripes = True
            yield table
    
    def on_mount(self) -> None:
        """Called when the widget is mounted to the DOM."""
        self.border_title = "Tag Schema"
        self.load_schema_data()
                
    def load_schema_data(self, highlighted_tags=None, show_no_tags_warning=False):
        """Load and display all schema data in flat table format with optional highlighting."""
        try:
            self.schema_data = self.tag_schema.load_schema()
            table = self.query_one("#schema-table")
            table.clear(columns=True)
            table.add_column("", width=50)
            table.add_row("", key="blank_start")

            if not self.schema_data:
                table.add_row("No tag schema found")
                table.update_selected_keys(set())
                table.update_error_keys(set())
                return

            error_keys = set()
            if show_no_tags_warning:
                warning_text = Text("⚠ No tag data for song")
                table.add_row(warning_text, key="warning_no_tags")
                error_keys.add("warning_no_tags")
                table.add_row("", key="blank_warning")

            category_count = len(self.schema_data)
            current_category = 0
            selected_keys = set()

            for category, values in self.schema_data.items():
                current_category += 1
                category_text = Text(category.title(), style="bold white")
                table.add_row(category_text, key=f"category_{category}")

                if isinstance(values, list):
                    sorted_values = sorted(values)
                    for value in sorted_values:
                        row_key = f"tag_{category}_{value}"
                        if highlighted_tags and category in highlighted_tags:
                            song_values = highlighted_tags[category]
                            if isinstance(song_values, list) and value in song_values:
                                value_text = Text(f"✓ {value}")
                                table.add_row(value_text, key=row_key)
                                selected_keys.add(row_key)
                            else:
                                table.add_row(f"  {value}", key=row_key)
                        else:
                            table.add_row(f"  {value}", key=row_key)
                elif isinstance(values, dict) and values.get("type") == "rating":
                    max_rating = values.get("max_rating", 5)
                    for i in range(1, max_rating + 1):
                        row_key = f"rating_{category}_{i}"
                        if highlighted_tags and category in highlighted_tags:
                            song_rating = highlighted_tags[category]
                            if isinstance(song_rating, (int, float)) and int(song_rating) == i:
                                rating_text = Text(f"✓ {i}")
                                table.add_row(rating_text, key=row_key)
                                selected_keys.add(row_key)
                            else:
                                table.add_row(f"  {i}", key=row_key)
                        else:
                            table.add_row(f"  {i}", key=row_key)

                if current_category < category_count:
                    table.add_row("", key=f"blank_{category}")

            table.update_selected_keys(selected_keys)
            table.update_error_keys(error_keys)

        except Exception as e:
            table = self.query_one("#schema-table")
            table.clear(columns=True)
            table.add_column("")
            table.add_row("")
            table.add_row(f"Error loading schema: {str(e)}")
            table.update_selected_keys(set())
            table.update_error_keys(set())
    
    def _check_song_has_tags(self, song_data: dict) -> bool:
        """Check if a song has any tags from the tag schema."""
        if not song_data:
            return False

        tags = song_data.get('tags')

        if not tags or not isinstance(tags, dict) or len(tags) == 0:
            return False

        for category, value in tags.items():
            if value is not None:
                if isinstance(value, (list, str)) and len(value) > 0:
                    return True
                elif isinstance(value, dict) and value.get("type") == "rating":
                    return True
                elif isinstance(value, (int, float)) and value > 0:
                    return True

        return False

    def highlight_song_tags(self, song_data):
        """Highlight tags in the schema that match the selected song."""
        self.current_song = song_data
        if song_data:
            has_tags = self._check_song_has_tags(song_data)
            if has_tags:
                self.load_schema_data(song_data.get('tags'), show_no_tags_warning=False)
            else:
                self.load_schema_data(None, show_no_tags_warning=True)
        else:
            self.load_schema_data()

    def on_data_table_row_selected(self, event) -> None:
        """Handle tag selection in the schema table."""
        if event.data_table.id == "schema-table" and self.current_song:
            row_key = event.row_key.value

            if row_key.startswith("blank_") or row_key.startswith("category_") or row_key.startswith("warning_"):
                return

            if row_key.startswith("tag_"):
                parts = row_key.split("_", 2)
                if len(parts) >= 3:
                    category = parts[1]
                    value = parts[2]
                    self.toggle_tag(category, value)

            elif row_key.startswith("rating_"):
                parts = row_key.split("_", 2)
                if len(parts) >= 3:
                    category = parts[1]
                    rating = parts[2]
                    self.set_rating(category, rating)

    def toggle_tag(self, category: str, value: str):
        """Toggle a tag value for the current song."""
        if not self.current_song:
            return

        file_path = Path(self.current_song['filepath'])
        current_tags = self.current_song.get('tags') or {}

        is_currently_set = False
        if category in current_tags:
            song_values = current_tags[category]
            if isinstance(song_values, list) and value in song_values:
                is_currently_set = True

        if is_currently_set:
            success = self.tag_service.remove_tag_from_file(file_path, category, value)
        else:
            success = self.tag_service.add_tag_to_file(file_path, category, value)

        if success:
            self.update_song_tags_in_database()

    def set_rating(self, category: str, rating: str):
        """Set a rating value for the current song."""
        if not self.current_song:
            return

        file_path = Path(self.current_song['filepath'])
        success = self.tag_service.set_rating_value(file_path, category, rating)

        if success:
            self.update_song_tags_in_database()

    def update_song_tags_in_database(self):
        """Update the song's tags in the database after file modification."""
        if not self.current_song:
            return

        file_path = Path(self.current_song['filepath'])
        new_tags = self.tag_service.build_tags_json_from_file(file_path)

        db = SessionLocal()
        try:
            song = db.query(Song).filter(Song.id == self.current_song['id']).first()
            if song:
                song.tags = new_tags
                db.commit()
                self.current_song['tags'] = new_tags
                self.highlight_song_tags(self.current_song)

                has_tags = self._check_song_has_tags(self.current_song)
                self.post_message(SongTagsUpdated(self.current_song['id'], has_tags, new_tags))
        finally:
            db.close()


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

    #songs-table > .datatable--cursor {
        background: $success-muted !important;
        color: $text-success !important;
        text-style: bold !important;
    }

    #songs-table .datatable--cursor {
        color: $text-success !important;
        text-style: bold !important;
    }

    #songs-table .datatable--cursor .datatable--cell {
        color: $text-success !important;
        text-style: bold !important;
    }

    #songs-table .datatable--cursor * {
        color: $text-success !important;
        text-style: bold !important;
    }
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

    #schema-table > .datatable--row-odd {
        background: #0f0f0f;
    }

    #schema-table > .datatable--row-even {
        background: #0a0a0a;
    }

    #schema-table > .datatable--row:hover,
    #schema-table > .datatable--row-odd:hover,
    #schema-table > .datatable--row-even:hover {
        background: #2a2a2a !important;
        color: #cccccc !important;
    }

    #schema-table .tag-selected {
        color: #dddddd !important;
        text-style: bold;
    }

    #schema-table .tag-unselected {
        color: #aaaaaa;
    }

    #schema-table > .datatable--row:hover .tag-unselected,
    #schema-table > .datatable--row:hover .tag-selected {
        background: #3a3a3a;
    }
    #table-container {
        height: 1fr;
        width: 4fr;
    }
    
    #songs-table {
        height: 1fr;
        width: 100%;
        scrollbar-size: 0 0;
    }

    DataTable > .datatable--row {
        height: 1;
        padding: 0;
        margin: 0;
    }

    #songs-content {
        width: 100%;
        height: 1fr;
    }

    #songs-table {
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

    .waveform-sparkline {
        width: 100%;
        height: 1;
        margin: 0;
        padding: 0;
        border: none;
    }

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

    .waveform-sparkline > .sparkline--max-color { color: $success; }
    .waveform-sparkline > .sparkline--min-color { color: $warning; }

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