from typing import List, Optional
from sqlalchemy import Table, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, relationship, Mapped
from datetime import datetime, UTC
import uuid
from ..session import Base
from .artist import ArtistRole, Artist

# Association table for many-to-many relationship between songs and artists 
songs_artists = Table(
    'songs_artists',
    Base.metadata,
    Column('song_id', UUID(as_uuid=True), ForeignKey('songs.id')),
    Column('artist_id', UUID(as_uuid=True), ForeignKey('artists.id')),
    Column('role', ArtistRole, default=ArtistRole.PRIMARY)
)

class Song(Base):
    __tablename__ = "song"

    # Objective metadata with type hints
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    year: Mapped[int] = mapped_column(Integer)
    bpm: Mapped[float] = mapped_column(Float)
    key: Mapped[str] = mapped_column(String)
    remix_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('songs.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    # Relationships with type hints
    artists: Mapped[List[Artist]] = relationship("Artist", secondary=songs_artists, back_populates="songs")
    remix_of: Mapped[Optional["Song"]] = relationship("Song", back_populates="remixes", remote_side=[id])
    remixes: Mapped[Optional[List["Song"]]] = relationship("Song", back_populates="remix_of", foreign_keys=[remix_id])

    def __repr__(self) -> str:
        return f"<Song {self.title} by {', '.join(artist.name for artist in self.artists)}>"