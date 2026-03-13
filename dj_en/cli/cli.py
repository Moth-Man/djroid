import click
from dj_en.services.crate import Crate
from pathlib import Path
from ..db import init_db, get_db
from ..logging import setup_logging, get_logger
from ..config import LOG_LEVEL
from dj_en.services.tag_schema import TagSchema
from dj_en.services.tag import Tag
from dj_en.services.scan import Scan
from dj_en.services.tag_interactive import TagInteractive
from dj_en.services.drop import Drop
from dj_en.services.mutate import Mutate
from dj_en.services.migrate import Migrate
from dj_en.textual.app import run_gui

# Initialize logger for this module
logger = get_logger(__name__)

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """DJ-EN - An AI-assisted DJ tool suit."""
    # Initialize logging when CLI starts
    setup_logging(LOG_LEVEL)
    logger.info("Starting DJ-EN CLI")
    
    # If no command is provided, launch the GUI
    if ctx.invoked_subcommand is None:
        logger.info("No command provided, launching GUI")
        run_gui()

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

@cli.command()
@click.argument('directory', type=click.Path(exists=True), required=False)
@click.option('--file', type=click.Path(exists=True), help='Scan a single file instead of a directory')
@click.option('--no-progress', is_flag=True, help='Disable progress bar')
def scan(directory: str, file: str, no_progress: bool):
    """Scan a song or directory of songs into dj-en's database"""
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

@cli.command()
def drop():
    """Drop all database tables and reinitialize schema (for testing)"""
    logger.info("Starting database drop operation")
    try:
        drop_service = Drop()
        if drop_service.drop_and_reinit():
            click.echo("Database dropped and reinitialized successfully.")
        else:
            click.echo("Failed to drop and reinitialize database.", err=True)
    except Exception as e:
        logger.error(f"Failed to drop database: {str(e)}", exc_info=True)
        click.echo(f"Error dropping database: {str(e)}", err=True)

@cli.command()
@click.argument('input_files', nargs=-1, required=True, type=click.Path(exists=True))
@click.option('--mp3', 'target_format', flag_value='mp3', help='Convert to MP3 format')
@click.option('--wav', 'target_format', flag_value='wav', help='Convert to WAV format')
@click.option('--aiff', 'target_format', flag_value='aiff', help='Convert to AIFF format')
@click.option('--flac', 'target_format', flag_value='flac', help='Convert to FLAC format')
@click.option('--m4a', 'target_format', flag_value='m4a', help='Convert to M4A format')
@click.option('--ogg', 'target_format', flag_value='ogg', help='Convert to OGG format')
def mutate(input_files: tuple, target_format: str):
    """Convert audio files to different formats using ffmpeg"""
    logger.info("Starting audio file conversion")

    if not target_format:
        click.echo("Error: You must specify a target format using one of: --mp3, --wav, --aiff, --flac, --m4a, --ogg", err=True)
        return

    try:
        mutate_service = Mutate()

        # Convert paths to Path objects
        file_paths = [Path(f) for f in input_files]

        if len(file_paths) == 1:
            # Single file conversion
            success = mutate_service.convert_single_file(file_paths[0], target_format)
            if success:
                logger.info("Single file conversion completed successfully")
            else:
                logger.error("Single file conversion failed")
        else:
            # Multiple file conversion
            results = mutate_service.convert_multiple_files(file_paths, target_format)
            if results['success'] > 0:
                logger.info(f"Conversion completed: {results['success']} successful, {results['failed']} failed, {results['skipped']} skipped")
            else:
                logger.error("All conversions failed")

    except Exception as e:
        logger.error(f"Failed to convert files: {str(e)}", exc_info=True)
        click.echo(f"Error converting files: {str(e)}", err=True)


@cli.command()
@click.argument('directory', type=click.Path(exists=True), required=False)
@click.option('--file', type=click.Path(exists=True), help='Migrate a single file instead of a directory')
@click.option('--dry-run', is_flag=True, help='Show what would be done without moving files')
@click.option('--no-progress', is_flag=True, help='Disable progress bar')
def migrate(directory: str, file: str, dry_run: bool, no_progress: bool):
    """Migrate music files to directories based on metadata rules.

    Reads file metadata (genre, artist, etc.) and moves files to destination
    directories based on rules configured in the TUI settings.

    If no directory is specified, uses the current working directory.
    """
    logger.info("Starting migrate operation")
    try:
        migrate_service = Migrate()

        if file:
            # Migrate single file
            file_path = Path(file)
            success = migrate_service.migrate_single_file(file_path, dry_run=dry_run)
            if success:
                logger.info("Single file migration completed successfully")
            else:
                logger.error("Single file migration failed")
        else:
            # Migrate directory
            dir_path = Path(directory) if directory else Path.cwd()

            result = migrate_service.migrate_directory(
                dir_path,
                dry_run=dry_run,
                show_progress=not no_progress
            )

            if result['success'] > 0 or result['no_match'] > 0:
                logger.info(
                    f"Migration completed: {result['success']} moved, "
                    f"{result['failed']} failed, {result['skipped']} skipped"
                )
            else:
                logger.warning("No files were migrated")

    except Exception as e:
        logger.error(f"Failed to migrate files: {str(e)}", exc_info=True)
        click.echo(f"Error migrating files: {str(e)}", err=True)


if __name__ == '__main__':
    cli()