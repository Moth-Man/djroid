import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import box
from mutagen import File
from mutagen.id3 import ID3
from mutagen.aiff import AIFF
import numpy as np
import librosa
import soundfile as sf
from djroid.logging import get_logger
from djroid.db import init_db, get_db
from djroid.db.dao.song_dao import SongDAO
from djroid.services.tag import Tag

logger = get_logger(__name__)

class Scan:
    def __init__(self):
        self.console = Console()
        self.tag_service = Tag()
        self.waveform_points = 80  # Number of points in waveform preview
        
    def find_music_files(self, directory: Path) -> List[Path]:
        """Find all music files in the given directory recursively"""
        music_extensions = {'.mp3', '.aiff', '.wav', '.flac', '.m4a', '.ogg'}
        music_files = []
        
        logger.info(f"Scanning directory: {directory}")
        
        for ext in music_extensions:
            music_files.extend(directory.rglob(f'*{ext}'))
        
        return sorted(music_files)
    
    def get_comprehensive_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get comprehensive audio metadata from a music file"""
        metadata = {}
        
        try:
            audio = File(str(file_path))
            
            if audio is None:
                return metadata
            
            # Check if the file has tags
            if not hasattr(audio, 'tags') or audio.tags is None:
                return metadata
            
            # Comprehensive metadata fields with their tag keys
            tag_mappings = {
                'title': ['TIT2', 'TITLE', 'title'],
                'artist': ['TPE1', 'ARTIST', 'artist'],
                'album': ['TALB', 'ALBUM', 'album'],
                'genre': ['TCON', 'GENRE', 'genre'],
                'bpm': ['TBPM', 'BPM', 'bpm'],
                'key': ['TKEY', 'KEY', 'key'],
                'track': ['TRCK', 'TRACK', 'track'],
                'isrc': ['TSRC', 'ISRC', 'isrc'],
                'publisher': ['TPUB', 'PUBLISHER', 'publisher'],
                'encoded_by': ['TENC', 'ENCODED_BY', 'encoded_by'],
                'file_url': ['WXXX:URL', 'URL', 'file_url'],
                'publisher_url': ['WXXX:PUBLISHER_URL', 'PUBLISHER_URL', 'publisher_url'],
                'comment': ['COMM', 'COMMENT', 'comment'],
                'recording_time': ['TDRC', 'RECORDING_TIME', 'recording_time'],
                'release_time': ['TDRL', 'RELEASE_TIME', 'release_time'],
                'original_release_time': ['TDOR', 'ORIGINAL_RELEASE_TIME', 'original_release_time'],
                'date_time_original': ['TDTG', 'DATE_TIME_ORIGINAL', 'date_time_original']
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
            
            # Special handling for Rekordbox comment (COMM tag)
            try:
                if hasattr(audio.tags, 'getall'):
                    for comm in audio.tags.getall("COMM"):
                        if hasattr(comm, 'lang') and hasattr(comm, 'desc') and hasattr(comm, 'text'):
                            if comm.lang == "eng" and comm.desc == "":
                                metadata['comment'] = str(comm.text[0])
                                break
            except (KeyError, AttributeError, IndexError):
                pass
            
            # Convert BPM to float if it exists
            if 'bpm' in metadata:
                try:
                    metadata['bpm'] = float(metadata['bpm'])
                except (ValueError, TypeError):
                    metadata['bpm'] = None
            
            # Extract year from various date fields
            for date_field in ['recording_time', 'release_time', 'original_release_time', 'date_time_original']:
                if date_field in metadata:
                    try:
                        # Try to extract year from date string
                        year_str = metadata[date_field]
                        if year_str and len(year_str) >= 4:
                            year = int(year_str[:4])
                            metadata['year'] = year
                            break
                    except (ValueError, TypeError):
                        continue
            
            # Add file type information
            metadata['file_type'] = file_path.suffix.lower()
            metadata['file_size_mb'] = round(file_path.stat().st_size / (1024 * 1024), 2)
            
        except Exception as e:
            logger.warning(f"Could not read metadata from {file_path}: {e}")
        
        return metadata
    
    def build_tags_json(self, file_path: Path, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Build a tags JSON object based on the file's TXXX tags and the user's schema"""
        # Use the shared function from the tag service
        return self.tag_service.build_tags_json_from_file(file_path)
    
    def analyze_audio_quality(self, file_path: Path) -> float:
        """
        Analyze audio file and return quality score between 0.0 and 1.0
        
        Quality factors:
        - Bitrate (higher is better)
        - Sample rate (44.1kHz+ preferred) 
        - File format (lossless > high bitrate lossy)
        """
        try:
            # Get audio metadata using ffprobe
            metadata = self._get_audio_metadata(file_path)
            if not metadata:
                return 0.3  # Default low score for unreadable files
            
            # Extract key metrics
            bitrate = metadata.get('bit_rate', 0)
            sample_rate = metadata.get('sample_rate', 0)
            codec_name = metadata.get('codec_name', '').lower()
            
            # Convert to numeric values
            try:
                bitrate = int(bitrate) if bitrate else 0
                sample_rate = int(sample_rate) if sample_rate else 0
            except (ValueError, TypeError):
                bitrate = 0
                sample_rate = 0
            
            # Calculate quality score
            quality_score = 0.0
            
            # Bitrate scoring (40% of total score)
            if codec_name in ['flac', 'alac', 'pcm_s16le', 'pcm_s24le']:
                # Lossless formats get high bitrate score
                quality_score += 0.4
            elif bitrate >= 320000:  # 320kbps+
                quality_score += 0.4
            elif bitrate >= 256000:  # 256kbps
                quality_score += 0.32
            elif bitrate >= 192000:  # 192kbps
                quality_score += 0.24
            elif bitrate >= 128000:  # 128kbps
                quality_score += 0.16
            else:
                quality_score += 0.08
            
            # Sample rate scoring (30% of total score)
            if sample_rate >= 96000:  # High-res audio
                quality_score += 0.3
            elif sample_rate >= 48000:  # Professional standard
                quality_score += 0.28
            elif sample_rate >= 44100:  # CD quality
                quality_score += 0.25
            elif sample_rate >= 22050:  # Acceptable
                quality_score += 0.15
            else:
                quality_score += 0.05
            
            # File format bonus (30% of total score)
            if codec_name in ['flac', 'alac']:  # Lossless
                quality_score += 0.3
            elif codec_name in ['pcm_s16le', 'pcm_s24le']:  # Uncompressed
                quality_score += 0.28
            elif codec_name == 'mp3' and bitrate >= 320000:  # High quality MP3
                quality_score += 0.22
            elif codec_name == 'mp3' and bitrate >= 256000:  # Good MP3
                quality_score += 0.18
            elif codec_name == 'aac' and bitrate >= 256000:  # High quality AAC
                quality_score += 0.2
            else:
                quality_score += 0.1
            
            # Ensure score is between 0.0 and 1.0
            quality_score = max(0.0, min(1.0, quality_score))
            
            logger.debug(f"Quality analysis for {file_path.name}: bitrate={bitrate}, sample_rate={sample_rate}, codec={codec_name}, score={quality_score:.3f}")
            
            return quality_score
            
        except Exception as e:
            logger.warning(f"Failed to analyze audio quality for {file_path}: {e}")
            return 0.3  # Default score for analysis failures
    
    def generate_waveform_preview(self, file_path: Path) -> Optional[List[float]]:
        """
        Generate downsampled waveform preview with normalized amplitude values
        
        Returns list of ~80 float values between 0.0 and 1.0
        """
        try:
            # Load audio file using librosa (automatically handles mono conversion)
            samples, sample_rate = librosa.load(str(file_path), mono=True, sr=None)
            
            # samples are already normalized to [-1, 1] by librosa
            if len(samples) == 0:
                return [0.0] * self.waveform_points
            
            # Downsample to target number of points
            if len(samples) <= self.waveform_points:
                # If audio is very short, pad with zeros
                waveform = np.pad(samples, (0, max(0, self.waveform_points - len(samples))))[:self.waveform_points]
            else:
                # Downsample by taking RMS of chunks
                chunk_size = len(samples) // self.waveform_points
                waveform = []
                
                for i in range(self.waveform_points):
                    start_idx = i * chunk_size
                    end_idx = min((i + 1) * chunk_size, len(samples))
                    
                    if start_idx < len(samples):
                        chunk = samples[start_idx:end_idx]
                        # Use RMS (Root Mean Square) for better amplitude representation
                        rms = np.sqrt(np.mean(chunk ** 2))
                        waveform.append(float(rms))
                    else:
                        waveform.append(0.0)
                
                waveform = np.array(waveform)
            
            # Convert to absolute values and normalize to [0, 1] range for display
            waveform = np.abs(waveform)
            if len(waveform) > 0:
                max_amplitude = np.max(waveform)
                if max_amplitude > 0:
                    waveform = waveform / max_amplitude
            
            # Convert to list and ensure all values are between 0 and 1
            waveform_list = [max(0.0, min(1.0, float(val))) for val in waveform]
            
            logger.debug(f"Generated waveform for {file_path.name}: {len(waveform_list)} points, max={max(waveform_list):.3f}")
            
            return waveform_list
            
        except Exception as e:
            logger.warning(f"Failed to generate waveform for {file_path}: {e}")
            return None
    
    def _get_audio_metadata(self, file_path: Path) -> Optional[dict]:
        """Get audio metadata using ffprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.warning(f"ffprobe failed for {file_path}: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            
            # Find the first audio stream
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    return stream
            
            return None
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to get metadata for {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting metadata for {file_path}: {e}")
            return None
    
    def get_color_gradient(self, quality_score: float) -> Tuple[str, str]:
        """
        Get color gradient based on quality score
        
        Returns tuple of (primary_color, secondary_color) for gradient
        """
        if quality_score >= 0.85:
            return ("green", "yellow")  # High quality: green with yellow highlights
        elif quality_score >= 0.6:
            return ("yellow", "red")    # Medium quality: yellow with red warnings
        else:
            return ("red", "bright_red")    # Low quality: red with bright red emphasis
    
    def scan_single_file(self, file_path: Path, db_session) -> bool:
        """Scan a single music file and add/update it in the database"""
        try:
            song_dao = SongDAO(db_session)
            
            # Get comprehensive metadata
            metadata = self.get_comprehensive_metadata(file_path)
            
            # Get tags JSON using the shared function
            tags_json = self.tag_service.build_tags_json_from_file(file_path)
            
            # Perform audio analysis
            quality_score = self.analyze_audio_quality(file_path)
            waveform_preview = self.generate_waveform_preview(file_path)
            
            # Create or update the song in the database
            song = song_dao.create_or_update_song(
                filepath=str(file_path.resolve()),
                title=metadata.get('title'),
                artist=metadata.get('artist'),
                album=metadata.get('album'),
                genre=metadata.get('genre'),
                year=metadata.get('year'),
                bpm=metadata.get('bpm'),
                key=metadata.get('key'),
                track=metadata.get('track'),
                isrc=metadata.get('isrc'),
                publisher=metadata.get('publisher'),
                encoded_by=metadata.get('encoded_by'),
                file_url=metadata.get('file_url'),
                publisher_url=metadata.get('publisher_url'),
                comment=metadata.get('comment'),
                recording_time=metadata.get('recording_time'),
                release_time=metadata.get('release_time'),
                original_release_time=metadata.get('original_release_time'),
                date_time_original=metadata.get('date_time_original'),
                file_type=metadata.get('file_type'),
                file_size_mb=metadata.get('file_size_mb'),
                tags=tags_json if tags_json else None,
                quality_score=quality_score,
                waveform_preview=waveform_preview
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
