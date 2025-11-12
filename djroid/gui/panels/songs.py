"""Songs panel widget for the djroid GUI."""

from math import sin
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, DataTable, Button, Sparkline
from textual import events
from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip

from ..colors import HighlightColors
from ..messages import SongSelected, SongTagsUpdated
from ...db.session import SessionLocal
from ...db.models.song import Song


class SongsDataTable(DataTable):
    """Custom DataTable for songs that highlights rows with no tags."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.no_tags_row_keys = set()

    def render_line(self, y: int):
        """Render a line, applying warning styling to rows with no tags."""
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
