"""Custom messages for the dj-en GUI."""

from textual.message import Message


class SongSelected(Message):
    """Message sent when a song is selected."""

    def __init__(self, song_data: dict) -> None:
        super().__init__()
        self.song_data = song_data


class SongTagsUpdated(Message):
    """Message sent when a song's tags are updated."""

    def __init__(self, song_id: int, has_tags: bool, new_tags: dict) -> None:
        super().__init__()
        self.song_id = song_id
        self.has_tags = has_tags
        self.new_tags = new_tags


class SettingsCategorySelected(Message):
    """Message sent when a settings category is selected."""

    def __init__(self, category: str) -> None:
        super().__init__()
        self.category = category


class TabChanged(Message):
    """Message sent when navigation tab changes."""

    def __init__(self, tab: str) -> None:
        super().__init__()
        self.tab = tab  # "library", "chat", or "settings"
