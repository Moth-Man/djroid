from dj_en.db.dao.base_dao import BaseDAO
from dj_en.db.models.song import Song
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import uuid
from pathlib import Path

class SongDAO(BaseDAO[Song]):
    def __init__(self, db: Session):
        super().__init__(Song, db)

    def create(self) -> Song:
        """Create a new song record (required by BaseDAO)"""
        song = Song()
        self.db.add(song)
        self.db.commit()
        self.db.refresh(song)
        return song

    def create_song(self, 
                   filepath: str,
                   title: Optional[str] = None,
                   artist: Optional[str] = None,
                   album: Optional[str] = None,
                   genre: Optional[str] = None,
                   year: Optional[int] = None,
                   bpm: Optional[float] = None,
                   key: Optional[str] = None,
                   track: Optional[str] = None,
                   isrc: Optional[str] = None,
                   publisher: Optional[str] = None,
                   encoded_by: Optional[str] = None,
                   file_url: Optional[str] = None,
                   publisher_url: Optional[str] = None,
                   comment: Optional[str] = None,
                   recording_time: Optional[str] = None,
                   release_time: Optional[str] = None,
                   original_release_time: Optional[str] = None,
                   date_time_original: Optional[str] = None,
                   file_type: Optional[str] = None,
                   file_size_mb: Optional[float] = None,
                   tags: Optional[Dict[str, Any]] = None,
                   quality_score: Optional[float] = None,
                   waveform_preview: Optional[List[float]] = None) -> Song:
        """Create a new song record"""
        song = Song(
            filepath=filepath,
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            year=year,
            bpm=bpm,
            key=key,
            track=track,
            isrc=isrc,
            publisher=publisher,
            encoded_by=encoded_by,
            file_url=file_url,
            publisher_url=publisher_url,
            comment=comment,
            recording_time=recording_time,
            release_time=release_time,
            original_release_time=original_release_time,
            date_time_original=date_time_original,
            file_type=file_type,
            file_size_mb=file_size_mb,
            tags=tags,
            quality_score=quality_score,
            waveform_preview=waveform_preview
        )
        self.db.add(song)
        self.db.commit()
        self.db.refresh(song)
        return song

    def get_by_filepath(self, filepath: str) -> Optional[Song]:
        """Get a song by its filepath"""
        return self.db.query(Song).filter(Song.filepath == filepath).first()

    def update_song(self, 
                   filepath: str,
                   title: Optional[str] = None,
                   artist: Optional[str] = None,
                   album: Optional[str] = None,
                   genre: Optional[str] = None,
                   year: Optional[int] = None,
                   bpm: Optional[float] = None,
                   key: Optional[str] = None,
                   track: Optional[str] = None,
                   isrc: Optional[str] = None,
                   publisher: Optional[str] = None,
                   encoded_by: Optional[str] = None,
                   file_url: Optional[str] = None,
                   publisher_url: Optional[str] = None,
                   comment: Optional[str] = None,
                   recording_time: Optional[str] = None,
                   release_time: Optional[str] = None,
                   original_release_time: Optional[str] = None,
                   date_time_original: Optional[str] = None,
                   file_type: Optional[str] = None,
                   file_size_mb: Optional[float] = None,
                   tags: Optional[Dict[str, Any]] = None,
                   quality_score: Optional[float] = None,
                   waveform_preview: Optional[List[float]] = None) -> Optional[Song]:
        """Update an existing song record"""
        song = self.get_by_filepath(filepath)
        if not song:
            return None
        
        # Update only provided fields
        if title is not None:
            song.title = title
        if artist is not None:
            song.artist = artist
        if album is not None:
            song.album = album
        if genre is not None:
            song.genre = genre
        if year is not None:
            song.year = year
        if bpm is not None:
            song.bpm = bpm
        if key is not None:
            song.key = key
        if track is not None:
            song.track = track
        if isrc is not None:
            song.isrc = isrc
        if publisher is not None:
            song.publisher = publisher
        if encoded_by is not None:
            song.encoded_by = encoded_by
        if file_url is not None:
            song.file_url = file_url
        if publisher_url is not None:
            song.publisher_url = publisher_url
        if comment is not None:
            song.comment = comment
        if recording_time is not None:
            song.recording_time = recording_time
        if release_time is not None:
            song.release_time = release_time
        if original_release_time is not None:
            song.original_release_time = original_release_time
        if date_time_original is not None:
            song.date_time_original = date_time_original
        if file_type is not None:
            song.file_type = file_type
        if file_size_mb is not None:
            song.file_size_mb = file_size_mb
        if tags is not None:
            song.tags = tags
        if quality_score is not None:
            song.quality_score = quality_score
        if waveform_preview is not None:
            song.waveform_preview = waveform_preview
        
        self.db.add(song)
        self.db.commit()
        self.db.refresh(song)
        return song

    def create_or_update_song(self, 
                            filepath: str,
                            title: Optional[str] = None,
                            artist: Optional[str] = None,
                            album: Optional[str] = None,
                            genre: Optional[str] = None,
                            year: Optional[int] = None,
                            bpm: Optional[float] = None,
                            key: Optional[str] = None,
                            track: Optional[str] = None,
                            isrc: Optional[str] = None,
                            publisher: Optional[str] = None,
                            encoded_by: Optional[str] = None,
                            file_url: Optional[str] = None,
                            publisher_url: Optional[str] = None,
                            comment: Optional[str] = None,
                            recording_time: Optional[str] = None,
                            release_time: Optional[str] = None,
                            original_release_time: Optional[str] = None,
                            date_time_original: Optional[str] = None,
                            file_type: Optional[str] = None,
                            file_size_mb: Optional[float] = None,
                            tags: Optional[Dict[str, Any]] = None,
                            quality_score: Optional[float] = None,
                            waveform_preview: Optional[List[float]] = None) -> Song:
        """Create a new song or update existing one"""
        existing_song = self.get_by_filepath(filepath)
        if existing_song:
            return self.update_song(
                filepath=filepath,
                title=title,
                artist=artist,
                album=album,
                genre=genre,
                year=year,
                bpm=bpm,
                key=key,
                track=track,
                isrc=isrc,
                publisher=publisher,
                encoded_by=encoded_by,
                file_url=file_url,
                publisher_url=publisher_url,
                comment=comment,
                recording_time=recording_time,
                release_time=release_time,
                original_release_time=original_release_time,
                date_time_original=date_time_original,
                file_type=file_type,
                file_size_mb=file_size_mb,
                tags=tags,
                quality_score=quality_score,
                waveform_preview=waveform_preview
            )
        else:
            return self.create_song(
                filepath=filepath,
                title=title,
                artist=artist,
                album=album,
                genre=genre,
                year=year,
                bpm=bpm,
                key=key,
                track=track,
                isrc=isrc,
                publisher=publisher,
                encoded_by=encoded_by,
                file_url=file_url,
                publisher_url=publisher_url,
                comment=comment,
                recording_time=recording_time,
                release_time=release_time,
                original_release_time=original_release_time,
                date_time_original=date_time_original,
                file_type=file_type,
                file_size_mb=file_size_mb,
                tags=tags,
                quality_score=quality_score,
                waveform_preview=waveform_preview
            )

    def delete_by_filepath(self, filepath: str) -> bool:
        """Delete a song by its filepath"""
        song = self.get_by_filepath(filepath)
        if song:
            self.db.delete(song)
            self.db.commit()
            return True
        return False

    def get_all_songs(self, skip: int = 0, limit: int = 100) -> List[Song]:
        """Get all songs with pagination"""
        return self.db.query(Song).offset(skip).limit(limit).all()

    def search_songs(self, 
                    title: Optional[str] = None,
                    artist: Optional[str] = None,
                    genre: Optional[str] = None,
                    bpm_min: Optional[float] = None,
                    bpm_max: Optional[float] = None,
                    key: Optional[str] = None,
                    year_min: Optional[int] = None,
                    year_max: Optional[int] = None,
                    isrc: Optional[str] = None,
                    publisher: Optional[str] = None) -> List[Song]:
        """Search songs by various criteria"""
        query = self.db.query(Song)
        
        if title:
            query = query.filter(Song.title.ilike(f"%{title}%"))
        if artist:
            query = query.filter(Song.artist.ilike(f"%{artist}%"))
        if genre:
            query = query.filter(Song.genre.ilike(f"%{genre}%"))
        if bpm_min is not None:
            query = query.filter(Song.bpm >= bpm_min)
        if bpm_max is not None:
            query = query.filter(Song.bpm <= bpm_max)
        if key:
            query = query.filter(Song.key.ilike(f"%{key}%"))
        if year_min is not None:
            query = query.filter(Song.year >= year_min)
        if year_max is not None:
            query = query.filter(Song.year <= year_max)
        if isrc:
            query = query.filter(Song.isrc == isrc)
        if publisher:
            query = query.filter(Song.publisher.ilike(f"%{publisher}%"))
        
        return query.all()

    def get_songs_by_tag(self, tag_category: str, tag_value: Optional[str] = None) -> List[Song]:
        """Get songs that have specific tags"""
        query = self.db.query(Song)
        
        if tag_value:
            # Search for songs with specific tag value
            query = query.filter(Song.tags[tag_category].astext.contains(tag_value))
        else:
            # Search for songs with any value in the tag category
            query = query.filter(Song.tags.has_key(tag_category))
        
        return query.all()

    def get_songs_by_bpm_range(self, min_bpm: float, max_bpm: float) -> List[Song]:
        """Get songs within a BPM range"""
        return self.db.query(Song).filter(
            Song.bpm >= min_bpm,
            Song.bpm <= max_bpm
        ).all()

    def get_songs_by_key(self, key: str) -> List[Song]:
        """Get songs by musical key"""
        return self.db.query(Song).filter(Song.key.ilike(f"%{key}%")).all()

    def get_songs_by_year(self, year: int) -> List[Song]:
        """Get songs from a specific year"""
        return self.db.query(Song).filter(Song.year == year).all()

    def get_songs_by_publisher(self, publisher: str) -> List[Song]:
        """Get songs by publisher/label"""
        return self.db.query(Song).filter(Song.publisher.ilike(f"%{publisher}%")).all()