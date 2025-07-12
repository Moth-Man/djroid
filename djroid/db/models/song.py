from typing import List, Optional, Dict, Any
from sqlalchemy import Integer, String, Float, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import mapped_column, Mapped
from datetime import datetime, UTC
import uuid
from ..session import Base

class Song(Base):
    __tablename__ = "songs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Basic metadata fields
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    artist: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    album: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    genre: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    date: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Year as string for flexibility
    bpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    key: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    
    # File information
    filepath: Mapped[str] = mapped_column(Text, nullable=False, index=True, unique=True)
    
    # Tags JSON object
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    def __repr__(self) -> str:
        return f"<Song {self.title or 'Unknown'} by {self.artist or 'Unknown'} ({self.filepath})>"