from .session import Base, engine, get_db
from .models.song import Song
from .models.tag import Tag

# Create all tables
def init_db():
    Base.metadata.create_all(bind=engine) 