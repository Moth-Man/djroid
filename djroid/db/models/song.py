from typing import List, Optional, Dict, Any
from sqlalchemy import Integer, String, Float, DateTime, Text, ARRAY
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
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    bpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    key: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    
    # Additional metadata fields
    track: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    isrc: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    publisher: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    encoded_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    publisher_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Date/time fields
    recording_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    release_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_release_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    date_time_original: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # File information
    filepath: Mapped[str] = mapped_column(Text, nullable=False, index=True, unique=True)
    file_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_size_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Tags JSON object
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, index=True)
    
    # Audio analysis fields
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    waveform_preview: Mapped[Optional[List[float]]] = mapped_column(ARRAY(Float), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    def __repr__(self) -> str:
        return f"<Song {self.title or 'Unknown'} by {self.artist or 'Unknown'} ({self.filepath})>"