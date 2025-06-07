from djroid.db.dao.base_dao import BaseDAO
from djroid.db.models.artist import Artist
from sqlalchemy.orm import Session
import uuid

class ArtistDAO(BaseDAO[Artist]):
    def __init__(self, db: Session):
        super().__init__(Artist, db)

    def create(self, name: str) -> Artist:
        artist = Artist(name=name)
        self.db.add(artist)
        self.db.commit()
        self.db.refresh(artist)
        return artist