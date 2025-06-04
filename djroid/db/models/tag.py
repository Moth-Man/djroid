from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from ..session import Base

# Association table for many-to-many relationship between songs and tags
song_tags = Table(
    'song_tags',
    Base.metadata,
    Column('song_id', Integer, ForeignKey('songs.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    # Relationships
    songs = relationship("Song", secondary=song_tags, back_populates="tags")

    def __repr__(self):
        return f"<Tag {self.name}>" 