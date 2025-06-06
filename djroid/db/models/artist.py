from typing import List
from enum import Enum
from sqlalchemy import Table, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, relationship, Mapped
from datetime import datetime
import uuid
from ..session import Base
from .song import songs_artists

class ArtistRole(Enum):
    PRIMARY = "primary"
    FEATURE = "feature"
    ORIGINAL_ARTIST = "original_artist"
    PRODUCER = "producer"

class Artist(Base):
    __tablename__ = "artist"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    songs: Mapped[List["Song"]] = relationship("Song", secondary=songs_artists, back_populates="artists")

    def __repr__(self) -> str:
        return f"<Artist {self.name}>"