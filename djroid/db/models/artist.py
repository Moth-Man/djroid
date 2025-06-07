from typing import List
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import mapped_column, relationship, Mapped
from datetime import datetime, UTC
import uuid
from ..session import Base
from .associations import songs_artists

class Artist(Base):
    __tablename__ = "artists"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    # Relationships
    songs: Mapped[List["Song"]] = relationship("Song", secondary=songs_artists, back_populates="artists")

    def __repr__(self) -> str:
        return f"<Artist {self.name}>"