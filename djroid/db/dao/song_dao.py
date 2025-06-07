from djroid.db.dao.base_dao import BaseDAO
from djroid.db.models.song import Song
from sqlalchemy.orm import Session
import uuid

class SongDAO(BaseDAO[Song]):
    def __init__(self, db: Session):
        super().__init__(Song, db)

    def create(self, bpm: int, title: str, artist_id: uuid.UUID) -> Song:
        song = Song(bpm=bpm, title=title, artist_id=artist_id)
        self.db.add(song)
        self.db.commit()
        self.db.refresh(song)
        return song