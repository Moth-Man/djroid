"""Tag schema panel widget for the djroid GUI."""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, DataTable
from textual.reactive import reactive
from rich.text import Text
from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip

from ..colors import HighlightColors
from ..messages import SongTagsUpdated
from ...services.tag_schema import TagSchema
from ...services.tag import Tag
from ...db.session import SessionLocal
from ...db.models.song import Song


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
