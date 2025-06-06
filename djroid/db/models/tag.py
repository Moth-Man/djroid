from sqlalchemy import Column, String, Table, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from ..session import Base

# Association table for many-to-many relationship between songs and tags
song_tags = Table(
    'song_tags',
    Base.metadata,
    Column('song_id', UUID(as_uuid=True), ForeignKey('songs.id')),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id'))
)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, unique=True, index=True)
    category = Column(String, index=True)

    # Relationships
    songs = relationship("Song", secondary=song_tags, back_populates="tags")

    def __repr__(self):
        return f"<Tag {self.name}>" 