import click
from djroid.services.crate import Crate
from pathlib import Path
from ..db import init_db, get_db
from ..logging import setup_logging, get_logger
from ..config import LOG_LEVEL
from djroid.services.tag_schema import TagSchema
from djroid.services.tag import Tag
from djroid.services.scan import Scan
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
@click.option('--path', type=click.Path(), help='Output directory for generated playlists')
@click.option('--usb', is_flag=True, help='Generate Rekordbox-compatible XML playlist')
@click.argument('prompt', required=True)
def crate(path: str, usb: bool, prompt: str):
    """Generate a curated playlist based on user prompt."""
    logger.info(f"Creating crate with prompt: {prompt}")
    try:
        crate_service = Crate()
        result = crate_service.generate_crate(prompt=prompt, output_path=path, usb_format=usb)
        
        if result["success"]:
            logger.info(f"Successfully created crate: {result['playlist_path']}")
            click.echo(f"✅ Crate generated successfully!")
            click.echo(f"📁 Output: {result['playlist_path']}")
            click.echo(f"🎵 Songs: {result['song_count']} ({result['duration']})")
        else:
            logger.error(f"Failed to create crate: {result['error']}")
            click.echo(f"❌ Error creating crate: {result['error']}", err=True)
            
    except Exception as e:
        logger.error(f"Failed to create crate: {str(e)}", exc_info=True)
        click.echo(f"❌ Error creating crate: {str(e)}", err=True)

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

@cli.command()
@click.argument('directory', type=click.Path(exists=True), required=False)
@click.option('--file', type=click.Path(exists=True), help='Scan a single file instead of a directory')
@click.option('--no-progress', is_flag=True, help='Disable progress bar')
def scan(directory: str, file: str, no_progress: bool):
    """Scan a song or directory of songs into djroid's database"""
    logger.info("Starting scan operation")
    try:
        scan_service = Scan()
        
        if file:
            # Scan single file
            file_path = Path(file)
            if not file_path.exists():
                click.echo(f"Error: File not found: {file}", err=True)
                return
            
            success = scan_service.scan_single_file_cli(file_path)
            if success:
                logger.info("Single file scan completed successfully")
            else:
                logger.error("Single file scan failed")
        else:
            # Scan directory
            dir_path = Path(directory) if directory else Path.cwd()
            if not dir_path.exists():
                click.echo(f"Error: Directory not found: {dir_path}", err=True)
                return
            
            result = scan_service.scan_directory(dir_path, show_progress=not no_progress)
            if result["success"]:
                logger.info("Directory scan completed successfully")
            else:
                logger.error(f"Directory scan failed: {result.get('error', 'Unknown error')}")
                click.echo(f"Error scanning directory: {result.get('error', 'Unknown error')}", err=True)
                
    except Exception as e:
        logger.error(f"Failed to scan songs: {str(e)}", exc_info=True)
        click.echo(f"Error scanning songs: {str(e)}", err=True)

if __name__ == '__main__':
    cli()