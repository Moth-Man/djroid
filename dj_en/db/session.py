from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.exc import OperationalError
from urllib.parse import urlparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from ..config import DATABASE_URL
from ..logging import get_logger

logger = get_logger(__name__)

class Base(DeclarativeBase):
    pass

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Database session generator for dependency injection.

    Yields a SQLAlchemy database session that is automatically closed when
    the context exits. Use this function with FastAPI dependencies or in
    'with' statements to ensure proper session cleanup.

    Yields:
        Session: SQLAlchemy database session
    """
    logger.debug("Creating new database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("Closing database session")
        db.close()

def check_database_connection():
    """
    Verify database accessibility by executing a test query.

    Attempts to connect to the database and execute a simple SELECT statement
    to validate that the database is reachable and responsive.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return False

def create_database_if_not_exists():
    """
    Create PostgreSQL database if it does not already exist.

    Parses the DATABASE_URL to extract connection details, connects to the
    PostgreSQL server (trying multiple system databases: target, postgres, template1),
    and creates the target database if it's not found.

    The function handles the following scenarios:
    - Database already exists: Returns successfully without changes
    - Database doesn't exist: Creates it with default encoding
    - Connection failures: Tries alternative system databases

    Returns:
        bool: True if database exists or was created successfully, False on error
    """
    try:
        # Parse the database URL to extract connection details
        parsed_url = urlparse(DATABASE_URL)
        db_name = parsed_url.path[1:]  # Remove leading slash
        host = parsed_url.hostname or 'localhost'
        port = parsed_url.port or 5432
        user = parsed_url.username
        password = parsed_url.password or ''
        
        # If no user specified, try to get current system user
        if not user:
            import getpass
            user = getpass.getuser()
            logger.info(f"No user specified in DATABASE_URL, using current user: {user}")
        
        # Try to connect to PostgreSQL server (not to the specific database)
        # First try connecting to the target database, if that fails, try 'postgres'
        conn = None
        for db_to_connect in [db_name, 'postgres', 'template1']:
            try:
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=db_to_connect
                )
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                logger.info(f"Connected to PostgreSQL using database: {db_to_connect}")
                break
            except psycopg2.OperationalError as e:
                if "does not exist" in str(e) and db_to_connect == db_name:
                    # Target database doesn't exist, try next one
                    continue
                else:
                    # Other connection error
                    raise e
        
        if not conn:
            raise Exception("Could not connect to any PostgreSQL database")
        
        cursor = conn.cursor()
        
        # Check if target database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Database '{db_name}' does not exist, creating it...")
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Database '{db_name}' created successfully")
        else:
            logger.info(f"Database '{db_name}' already exists")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        return False

def init_database():
    """
    Initialize the database and create all required tables.

    This is the main setup function that:
    1. Creates the database if it doesn't exist
    2. Verifies database connectivity
    3. Creates all tables defined in SQLAlchemy models

    Should be called once during application setup or when resetting the database.

    Returns:
        bool: True if initialization successful, False on error
    """
    try:
        # Create database if it doesn't exist
        if not create_database_if_not_exists():
            raise Exception("Cannot create database")
        
        # Check connection
        if not check_database_connection():
            raise Exception("Cannot connect to database")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def drop_database():
    """
    Drop all database tables - DESTRUCTIVE OPERATION.

    WARNING: This permanently deletes all tables and data. Use only for:
    - Development and testing
    - Database schema resets
    - Clean reinstallation

    Does NOT drop the database itself, only the tables within it.

    Returns:
        bool: True if tables dropped successfully, False on error
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        return False