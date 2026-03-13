from ..db.session import drop_database, init_database
from ..logging import get_logger

logger = get_logger(__name__)

class Drop:
    """Service for dropping and reinitializing the database"""

    def __init__(self):
        pass

    def drop_and_reinit(self) -> bool:
        """Drop all database tables and reinitialize schema"""
        try:
            logger.info("Dropping database tables...")
            if not drop_database():
                return False

            logger.info("Reinitializing database schema...")
            if not init_database():
                return False

            logger.info("Database drop and reinit completed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to drop and reinit database: {e}")
            return False