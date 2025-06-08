from .session import Base, engine, get_db
from .models.song import Song
from .models.tag import Tag
from ..logging import get_logger

logger = get_logger(__name__)

# Create all tables
def init_db():
    logger.info("Initializing database tables")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Successfully initialized database tables")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        raise 