from enum import Enum
from sqlalchemy import Table, Column, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID
from ..session import Base

class ArtistRole(Enum):
    PRIMARY = "primary"
    FEATURE = "feature"
    ORIGINAL_ARTIST = "original_artist"
    PRODUCER = "producer"

# Association table for many-to-many relationship between songs and artists 
songs_artists = Table(
    'songs_artists',
    Base.metadata,
    Column('song_id', UUID(as_uuid=True), ForeignKey('songs.id')),
    Column('artist_id', UUID(as_uuid=True), ForeignKey('artists.id')),
    Column('role', SQLAlchemyEnum(ArtistRole), default=ArtistRole.PRIMARY)
)