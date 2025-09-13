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
    logger.debug("Creating new database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("Closing database session")
        db.close()

def check_database_connection():
    """Check if the database is accessible"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return False

def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
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
    """Initialize the database and create all tables"""
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
    """Drop all tables (use with caution)"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        return False