import click
from pathlib import Path
from .db import init_db, get_db
from .ingestors import SongIngestor

@click.group()
def cli():
    """DJroid - A DJ's music library management tool."""
    pass

@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--recursive/--no-recursive', default=True, help='Recursively scan subdirectories')
def ingest(directory: str, recursive: bool):
    """Ingest music files from a directory into the database."""
    click.echo(f"Ingesting music files from {directory}...")
    
    # Initialize database
    init_db()
    
    # Get database session
    db = next(get_db())
    
    # Create ingestor and process files
    ingestor = SongIngestor(db)
    songs = ingestor.ingest_directory(directory, recursive=recursive)
    
    click.echo(f"Successfully ingested {len(songs)} songs.")

@cli.command()
def init():
    """Initialize the database."""
    click.echo("Initializing database...")
    init_db()
    click.echo("Database initialized successfully.")

if __name__ == '__main__':
    cli() 