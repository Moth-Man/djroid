import click
from djroid.services.crate import Crate
from pathlib import Path
from ..db import init_db, get_db
from ..logging import setup_logging, get_logger
from ..config import LOG_LEVEL
from djroid.services.tag_schema import TagSchema
from djroid.services.tag import Tag
from djroid.services.tag_interactive import TagInteractive

# Initialize logger for this module
logger = get_logger(__name__)

@click.group()
def cli():
    """DJroid - An AI-assisted DJ tool suit."""
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
        crate_service = Crate(name, file_path, prompt)
        crate_service.generate_crate()
        logger.info(f"Successfully created crate: {name}")
        click.echo("Crate created successfully.")
    except Exception as e:
        logger.error(f"Failed to create crate: {str(e)}", exc_info=True)
        click.echo(f"Error creating crate: {str(e)}", err=True)

@cli.command(name='tag-schema')
def tag_schema():
    """Setup your tagging schema with categories and values."""
    logger.info("Starting tag schema setup")
    try:
        tag_schema_service = TagSchema()
        tag_schema_service.setup_schema()
        logger.info("Tag schema setup completed successfully")
    except Exception as e:
        logger.error(f"Failed to setup tag schema: {str(e)}", exc_info=True)
        click.echo(f"Error setting up tag schema: {str(e)}", err=True)

@cli.command()
@click.argument('directory', type=click.Path(exists=True), required=False)
@click.option('--file', type=click.Path(exists=True), help='Tag a single file instead of a directory')
@click.option('--interactive/--no-interactive', default=True, help='Use interactive interface')
def tag(directory: str, file: str, interactive: bool):
    """Tag a song or list of songs"""
    logger.info("Starting tag operation")
    try:
        if file:
            # Tag single file
            file_path = Path(file)
            if interactive:
                tag_service = TagInteractive()
                tag_service.edit_file_tags_interactive(file_path)
            else:
                # Use enhanced tagging for --no-interactive mode
                tag_service = Tag()
                tag_service.tag_single_file(file_path)
        else:
            # Tag directory
            dir_path = Path(directory) if directory else Path.cwd()
            if interactive:
                tag_service = TagInteractive()
                tag_service.run_interactive_selector(dir_path)
            else:
                tag_service = Tag()
                tag_service.tag_songs(dir_path)
            
        logger.info("Tag operation completed successfully")
    except Exception as e:
        logger.error(f"Failed to tag songs: {str(e)}", exc_info=True)
        click.echo(f"Error tagging songs: {str(e)}", err=True)

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