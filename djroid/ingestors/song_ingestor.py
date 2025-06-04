import os
from pathlib import Path
from mutagen import File as MutagenFile
from sqlalchemy.orm import Session
from ..db.models import Song, Tag

class SongIngestor:
    def __init__(self, db: Session):
        self.db = db

    def ingest_file(self, file_path: str) -> Song:
        """Ingest a single music file and create a Song record."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get audio metadata using mutagen
        audio = MutagenFile(str(file_path))
        if audio is None:
            raise ValueError(f"Unsupported audio format: {file_path}")

        # Extract metadata
        title = audio.get('title', [file_path.stem])[0]
        artist = audio.get('artist', ['Unknown Artist'])[0]
        album = audio.get('album', ['Unknown Album'])[0]
        genre = audio.get('genre', ['Unknown Genre'])[0]
        year = audio.get('date', [None])[0]
        duration = audio.info.length if hasattr(audio.info, 'length') else None

        # Create song record
        song = Song(
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            year=int(year) if year and year.isdigit() else None,
            duration=duration,
            file_path=str(file_path.absolute())
        )

        # Add to database
        self.db.add(song)
        self.db.commit()
        self.db.refresh(song)

        return song

    def ingest_directory(self, directory: str, recursive: bool = True) -> list[Song]:
        """Ingest all music files in a directory."""
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        songs = []
        for file_path in directory.rglob('*') if recursive else directory.glob('*'):
            if file_path.is_file() and self._is_audio_file(file_path):
                try:
                    song = self.ingest_file(str(file_path))
                    songs.append(song)
                except Exception as e:
                    print(f"Error ingesting {file_path}: {e}")

        return songs

    @staticmethod
    def _is_audio_file(file_path: Path) -> bool:
        """Check if a file is an audio file based on its extension."""
        audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac'}
        return file_path.suffix.lower() in audio_extensions 