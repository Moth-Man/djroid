from djroid.db.dao.base_dao import BaseDAO
from djroid.db.models.song import Song
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import uuid
from pathlib import Path

class SongDAO(BaseDAO[Song]):
    def __init__(self, db: Session):
        super().__init__(Song, db)

    def create_song(self, 
                   filepath: str,
                   title: Optional[str] = None,
                   artist: Optional[str] = None,
                   album: Optional[str] = None,
                   genre: Optional[str] = None,
                   date: Optional[str] = None,
                   bpm: Optional[float] = None,
                   key: Optional[str] = None,
                   tags: Optional[Dict[str, Any]] = None) -> Song:
        """Create a new song record"""
        song = Song(
            filepath=filepath,
            title=title,
            artist=artist,
            album=album,
            genre=genre,
            date=date,
            bpm=bpm,
            key=key,
            tags=tags
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
                   date: Optional[str] = None,
                   bpm: Optional[float] = None,
                   key: Optional[str] = None,
                   tags: Optional[Dict[str, Any]] = None) -> Optional[Song]:
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
        if date is not None:
            song.date = date
        if bpm is not None:
            song.bpm = bpm
        if key is not None:
            song.key = key
        if tags is not None:
            song.tags = tags
        
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
                            date: Optional[str] = None,
                            bpm: Optional[float] = None,
                            key: Optional[str] = None,
                            tags: Optional[Dict[str, Any]] = None) -> Song:
        """Create a new song or update existing one"""
        existing_song = self.get_by_filepath(filepath)
        if existing_song:
            return self.update_song(
                filepath=filepath,
                title=title,
                artist=artist,
                album=album,
                genre=genre,
                date=date,
                bpm=bpm,
                key=key,
                tags=tags
            )
        else:
            return self.create_song(
                filepath=filepath,
                title=title,
                artist=artist,
                album=album,
                genre=genre,
                date=date,
                bpm=bpm,
                key=key,
                tags=tags
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
                    key: Optional[str] = None) -> List[Song]:
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
        
        return query.all()