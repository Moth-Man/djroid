from .session import Base, engine, get_db, init_database, check_database_connection
from .models.song import Song
from ..logging import get_logger

logger = get_logger(__name__)

# Create all tables
def init_db():
    logger.info("Initializing database tables")
    try:
        success = init_database()
        if success:
            logger.info("Successfully initialized database tables")
        else:
            logger.error("Failed to initialize database")
            raise Exception("Database initialization failed")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        raise 