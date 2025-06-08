import click
from djroid.cli.services.crate_service import CrateService
from pathlib import Path
from ..db import init_db, get_db
from ..logging import setup_logging, get_logger
from ..config import LOG_LEVEL

# Initialize logger for this module
logger = get_logger(__name__)

@click.group()
def cli():
    """DJroid - A DJ's music library management tool."""
    # Initialize logging when CLI starts
    setup_logging(LOG_LEVEL)
    logger.info("Starting DJroid CLI")
    pass

@cli.command()
@click.option('--prompt', required=True, help='The prompt to generate the crate from')
@click.option('--name', required=True, help='Name of the crate')
@click.option('--file-path', required=True, type=click.Path(), help='Path where the crate will be created')
def crate(prompt: str, name: str, file_path: str):
    """Create a crate."""
    logger.info(f"Creating crate '{name}' with prompt: {prompt}")
    try:
        crate_service = CrateService(name, file_path, prompt)
        crate_service.generate_crate()
        logger.info(f"Successfully created crate: {name}")
        click.echo("Crate created successfully.")
    except Exception as e:
        logger.error(f"Failed to create crate: {str(e)}", exc_info=True)
        click.echo(f"Error creating crate: {str(e)}", err=True)

if __name__ == '__main__':
    cli()

# @cli.command()
# @click.argument('directory', type=click.Path(exists=True))
# @click.option('--recursive/--no-recursive', default=True, help='Recursively scan subdirectories')
# def ingest(directory: str, recursive: bool):
#     """Ingest music files from a directory into the database."""
#     click.echo(f"Ingesting music files from {directory}...")
    
#     # Initialize database
#     init_db()
    
#     # Get database session
#     db = next(get_db())
    
#     # Create ingestor and process files
#     ingestor = SongIngestor(db)
#     songs = ingestor.ingest_directory(directory, recursive=recursive)
    
#     click.echo(f"Successfully ingested {len(songs)} songs.")

# @cli.command()
# def init():
#     """Initialize the database."""
#     click.echo("Initializing database...")
#     init_db()
#     click.echo("Database initialized successfully.")