import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import box
from mutagen import File
from mutagen.id3 import ID3
from mutagen.aiff import AIFF
from djroid.logging import get_logger
from djroid.db import init_db, get_db
from djroid.db.dao.song_dao import SongDAO
from djroid.services.tag import Tag

logger = get_logger(__name__)

class Scan:
    def __init__(self):
        self.console = Console()
        self.tag_service = Tag()
        
    def find_music_files(self, directory: Path) -> List[Path]:
        """Find all music files in the given directory recursively"""
        music_extensions = {'.mp3', '.aiff', '.wav', '.flac', '.m4a', '.ogg'}
        music_files = []
        
        logger.info(f"Scanning directory: {directory}")
        
        for ext in music_extensions:
            music_files.extend(directory.rglob(f'*{ext}'))
        
        return sorted(music_files)
    
    def get_audio_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get basic audio metadata from a music file"""
        metadata = {}
        
        try:
            audio = File(str(file_path))
            
            if audio is None:
                return metadata
            
            # Check if the file has tags
            if not hasattr(audio, 'tags') or audio.tags is None:
                return metadata
            
            # Common metadata fields with their tag keys
            tag_mappings = {
                'title': ['TIT2', 'TITLE', 'title'],
                'artist': ['TPE1', 'ARTIST', 'artist'],
                'album': ['TALB', 'ALBUM', 'album'],
                'date': ['TDRC', 'DATE', 'date'],
                'genre': ['TCON', 'GENRE', 'genre'],
                'bpm': ['TBPM', 'BPM', 'bpm'],
                'key': ['TKEY', 'KEY', 'key']
            }
            
            for field, possible_keys in tag_mappings.items():
                for key in possible_keys:
                    try:
                        # Try different ways to access the tag
                        if hasattr(audio.tags, 'get'):
                            value = audio.tags.get(key)
                            if value:
                                if hasattr(value, 'text'):
                                    metadata[field] = str(value.text[0])
                                else:
                                    metadata[field] = str(value)
                                break
                        elif hasattr(audio.tags, '__getitem__'):
                            value = audio.tags[key]
                            if value:
                                if hasattr(value, 'text'):
                                    metadata[field] = str(value.text[0])
                                else:
                                    metadata[field] = str(value)
                                break
                    except (KeyError, AttributeError, IndexError):
                        continue
            
            # Convert BPM to float if it exists
            if 'bpm' in metadata:
                try:
                    metadata['bpm'] = float(metadata['bpm'])
                except (ValueError, TypeError):
                    metadata['bpm'] = None
            
        except Exception as e:
            logger.warning(f"Could not read metadata from {file_path}: {e}")
        
        return metadata
    
    def get_file_tags(self, file_path: Path) -> Dict[str, List[str]]:
        """Get existing TXXX tags from a music file"""
        tags = {}
        
        try:
            audio = File(str(file_path))
            
            if audio is None:
                return tags
            
            # Handle MP3 files
            if file_path.suffix.lower() == '.mp3' and hasattr(audio, 'tags') and audio.tags:
                if hasattr(audio.tags, 'getall'):
                    for key in audio.tags.keys():
                        if key.startswith('TXXX:'):
                            category = key[5:]  # Remove 'TXXX:' prefix
                            values = audio.tags.getall(key)
                            tags[category] = [str(v) for v in values]
            
            # Handle AIFF and other files
            elif hasattr(audio, 'tags') and audio.tags:
                for key, value in audio.tags.items():
                    if key.startswith('TXXX:'):
                        category = key[5:]
                        if hasattr(value, 'text'):
                            # Handle comma-separated values
                            text_values = value.text
                            if isinstance(text_values, list):
                                # If it's already a list, use as is
                                tags[category] = [str(v) for v in text_values]
                            else:
                                # If it's a string, split by commas
                                tags[category] = [v.strip() for v in str(text_values).split(',')]
                        else:
                            # Fallback
                            tags[category] = [str(value)]
                        
        except Exception as e:
            logger.warning(f"Could not read tags from {file_path}: {e}")
        
        return tags
    
    def build_tags_json(self, file_path: Path, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Build a tags JSON object based on the file's TXXX tags and the user's schema"""
        # Use the shared function from the tag service
        return self.tag_service.build_tags_json_from_file(file_path)
    
    def scan_single_file(self, file_path: Path, db_session) -> bool:
        """Scan a single music file and add/update it in the database"""
        try:
            song_dao = SongDAO(db_session)
            
            # Get basic metadata
            metadata = self.get_audio_metadata(file_path)
            
            # Get tags JSON using the shared function
            tags_json = self.tag_service.build_tags_json_from_file(file_path)
            
            # Create or update the song in the database
            song = song_dao.create_or_update_song(
                filepath=str(file_path.resolve()),
                title=metadata.get('title'),
                artist=metadata.get('artist'),
                album=metadata.get('album'),
                genre=metadata.get('genre'),
                date=metadata.get('date'),
                bpm=metadata.get('bpm'),
                key=metadata.get('key'),
                tags=tags_json if tags_json else None
            )
            
            logger.debug(f"Processed file: {file_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            return False
    
    def scan_directory(self, directory: Path, show_progress: bool = True) -> Dict[str, Any]:
        """Scan a directory for music files and populate the database"""
        # Initialize database
        logger.info("Initializing database...")
        try:
            init_db()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return {"success": False, "error": str(e)}
        
        # Find music files
        logger.info(f"Scanning directory: {directory}")
        music_files = self.find_music_files(directory)
        
        if not music_files:
            logger.warning("No music files found in the directory")
            return {"success": True, "files_processed": 0, "files_updated": 0, "files_created": 0}
        
        logger.info(f"Found {len(music_files)} music files")
        
        # Process files
        processed_count = 0
        created_count = 0
        updated_count = 0
        error_count = 0
        
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task("Scanning music files...", total=len(music_files))
                
                for file_path in music_files:
                    progress.update(task, description=f"Processing {file_path.name}")
                    
                    try:
                        # Get database session
                        db_gen = get_db()
                        db_session = next(db_gen)
                        
                        # Check if file already exists in database
                        song_dao = SongDAO(db_session)
                        existing_song = song_dao.get_by_filepath(str(file_path.resolve()))
                        
                        # Process the file
                        success = self.scan_single_file(file_path, db_session)
                        
                        if success:
                            if existing_song:
                                updated_count += 1
                            else:
                                created_count += 1
                        else:
                            error_count += 1
                        
                        processed_count += 1
                        
                        # Close database session
                        db_gen.close()
                        
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")
                        error_count += 1
                        processed_count += 1
                    
                    progress.advance(task)
        else:
            # Process without progress bar
            for file_path in music_files:
                try:
                    # Get database session
                    db_gen = get_db()
                    db_session = next(db_gen)
                    
                    # Check if file already exists in database
                    song_dao = SongDAO(db_session)
                    existing_song = song_dao.get_by_filepath(str(file_path.resolve()))
                    
                    # Process the file
                    success = self.scan_single_file(file_path, db_session)
                    
                    if success:
                        if existing_song:
                            updated_count += 1
                        else:
                            created_count += 1
                    else:
                        error_count += 1
                    
                    processed_count += 1
                    
                    # Close database session
                    db_gen.close()
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    error_count += 1
                    processed_count += 1
        
        # Display results
        self.display_scan_results(processed_count, created_count, updated_count, error_count)
        
        return {
            "success": True,
            "files_processed": processed_count,
            "files_created": created_count,
            "files_updated": updated_count,
            "files_errors": error_count
        }
    
    def display_scan_results(self, processed: int, created: int, updated: int, errors: int):
        """Display scan results in a nice table"""
        table = Table(title="Scan Results", box=box.ROUNDED, show_lines=True)
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Count", style="green", justify="right")
        
        table.add_row("Files Processed", str(processed))
        table.add_row("Files Created", str(created))
        table.add_row("Files Updated", str(updated))
        table.add_row("Files with Errors", str(errors))
        
        self.console.print(table)
    
    def scan_single_file_cli(self, file_path: Path) -> bool:
        """Scan a single file from CLI"""
        try:
            # Initialize database
            init_db()
            
            # Get database session
            db_gen = get_db()
            db_session = next(db_gen)
            
            # Process the file
            success = self.scan_single_file(file_path, db_session)
            
            # Close database session
            db_gen.close()
            
            if success:
                self.console.print(f"[green]Successfully scanned: {file_path.name}[/green]")
            else:
                self.console.print(f"[red]Failed to scan: {file_path.name}[/red]")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to scan file {file_path}: {e}")
            self.console.print(f"[red]Error scanning {file_path.name}: {e}[/red]")
            return False
