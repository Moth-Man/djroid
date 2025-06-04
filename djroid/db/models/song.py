from sqlalchemy import Column, Integer, String, Float, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..session import Base

# Association table for many-to-many relationship between songs and playlists
song_playlist = Table(
    'song_playlist',
    Base.metadata,
    Column('song_id', Integer, ForeignKey('songs.id')),
    Column('playlist_id', Integer, ForeignKey('playlists.id'))
)

class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    artist = Column(String, index=True)
    album = Column(String, index=True)
    genre = Column(String, index=True)
    year = Column(Integer)
    duration = Column(Float)  # Duration in seconds
    file_path = Column(String, unique=True, index=True)
    bpm = Column(Float)  # Beats per minute
    key = Column(String)  # Musical key
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    playlists = relationship("Playlist", secondary=song_playlist, back_populates="songs")
    tags = relationship("Tag", secondary="song_tags", back_populates="songs")

    def __repr__(self):
        return f"<Song {self.title} by {self.artist}>" 