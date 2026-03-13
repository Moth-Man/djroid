import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import box
import shutil
from dj_en.logging import get_logger

logger = get_logger(__name__)

class Mutate:
    def __init__(self):
        self.console = Console()
        self.supported_formats = {
            'mp3': 'MP3',
            'wav': 'WAV',
            'aiff': 'AIFF',
            'flac': 'FLAC',
            'm4a': 'M4A',
            'ogg': 'OGG'
        }

        # Check if ffmpeg is available
        if not self._check_ffmpeg():
            self.console.print("[red]Error: ffmpeg is required for audio conversion but not found in PATH[/red]")
            self.console.print("Please install ffmpeg: https://ffmpeg.org/download.html")
            sys.exit(1)

    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available in the system"""
        return shutil.which('ffmpeg') is not None

    def _get_ffmpeg_codec_settings(self, target_format: str) -> Dict[str, str]:
        """Get appropriate codec settings for each format"""
        codec_settings = {
            'mp3': {
                'codec': 'libmp3lame',
                'extra_args': ['-b:a', '320k']  # High quality MP3
            },
            'wav': {
                'codec': 'pcm_s16le',
                'extra_args': []
            },
            'aiff': {
                'codec': 'pcm_s16le',
                'extra_args': []
            },
            'flac': {
                'codec': 'flac',
                'extra_args': ['-compression_level', '8']  # Max compression
            },
            'm4a': {
                'codec': 'aac',
                'extra_args': ['-b:a', '256k']  # High quality AAC
            },
            'ogg': {
                'codec': 'libvorbis',
                'extra_args': ['-q:a', '8']  # High quality Vorbis
            }
        }
        return codec_settings.get(target_format, {'codec': 'copy', 'extra_args': []})

    def _build_ffmpeg_command(self, input_file: Path, output_file: Path, target_format: str) -> List[str]:
        """Build the ffmpeg command for conversion"""
        codec_settings = self._get_ffmpeg_codec_settings(target_format)

        cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-acodec', codec_settings['codec'],
            '-map_metadata', '0',  # Preserve metadata
            '-y'  # Overwrite output file
        ]

        # Add format-specific arguments
        cmd.extend(codec_settings['extra_args'])

        # Add output file
        cmd.append(str(output_file))

        return cmd

    def _convert_file(self, input_file: Path, output_file: Path, target_format: str) -> bool:
        """Convert a single audio file using ffmpeg"""
        try:
            cmd = self._build_ffmpeg_command(input_file, output_file, target_format)

            # Run ffmpeg conversion
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per file
            )

            if result.returncode == 0:
                logger.info(f"Successfully converted {input_file.name} to {target_format.upper()}")
                return True
            else:
                logger.error(f"ffmpeg conversion failed for {input_file.name}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Conversion timeout for {input_file.name}")
            return False
        except Exception as e:
            logger.error(f"Error converting {input_file.name}: {e}")
            return False

    def _get_output_filename(self, input_file: Path, target_format: str) -> Path:
        """Generate output filename with new extension"""
        output_file = input_file.with_suffix(f'.{target_format}')

        # If output file already exists, add a suffix
        counter = 1
        while output_file.exists():
            stem = input_file.stem
            output_file = input_file.parent / f"{stem}_converted_{counter}.{target_format}"
            counter += 1

        return output_file

    def _validate_file(self, file_path: Path) -> bool:
        """Validate that the file is an audio file"""
        if not file_path.exists():
            self.console.print(f"[red]Error: File not found: {file_path}[/red]")
            return False

        audio_extensions = {'.mp3', '.wav', '.aiff', '.flac', '.m4a', '.ogg', '.aac'}
        if file_path.suffix.lower() not in audio_extensions:
            self.console.print(f"[red]Error: Not an audio file: {file_path}[/red]")
            return False

        return True

    def convert_single_file(self, input_file: Path, target_format: str) -> bool:
        """Convert a single audio file to the target format"""
        # Validate inputs
        if not self._validate_file(input_file):
            return False

        if target_format not in self.supported_formats:
            self.console.print(f"[red]Error: Unsupported target format: {target_format}[/red]")
            self.console.print(f"Supported formats: {', '.join(self.supported_formats.keys())}")
            return False

        # Check if file is already in target format
        if input_file.suffix.lower() == f'.{target_format}':
            self.console.print(f"[yellow]File is already in {target_format.upper()} format: {input_file.name}[/yellow]")
            return True

        # Generate output filename
        output_file = self._get_output_filename(input_file, target_format)

        # Display conversion info
        self.console.print(f"\n[bold blue]Converting:[/bold blue] {input_file.name}")
        self.console.print(f"[bold blue]Target:[/bold blue] {output_file.name}")

        # Perform conversion
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(f"Converting to {target_format.upper()}...", total=1)

            success = self._convert_file(input_file, output_file, target_format)
            progress.update(task, completed=1)

        if success:
            self.console.print(f"[green]✓ Conversion completed: {output_file.name}[/green]")

            # Show file sizes
            input_size = input_file.stat().st_size / (1024 * 1024)
            output_size = output_file.stat().st_size / (1024 * 1024)
            self.console.print(f"[dim]Input size: {input_size:.1f} MB | Output size: {output_size:.1f} MB[/dim]")

        else:
            self.console.print(f"[red]✗ Conversion failed for: {input_file.name}[/red]")

        return success

    def convert_multiple_files(self, input_files: List[Path], target_format: str) -> Dict[str, int]:
        """Convert multiple audio files to the target format"""
        if target_format not in self.supported_formats:
            self.console.print(f"[red]Error: Unsupported target format: {target_format}[/red]")
            self.console.print(f"Supported formats: {', '.join(self.supported_formats.keys())}")
            return {'success': 0, 'failed': 0, 'skipped': 0}

        # Filter and validate files
        valid_files = [f for f in input_files if self._validate_file(f)]

        if not valid_files:
            self.console.print("[red]No valid audio files to convert[/red]")
            return {'success': 0, 'failed': 0, 'skipped': 0}

        success_count = 0
        failed_count = 0
        skipped_count = 0

        self.console.print(f"\n[bold]Converting {len(valid_files)} files to {target_format.upper()}[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:

            overall_task = progress.add_task("Overall progress", total=len(valid_files))

            for i, input_file in enumerate(valid_files):
                # Check if already in target format
                if input_file.suffix.lower() == f'.{target_format}':
                    progress.console.print(f"[yellow]Skipping (already {target_format.upper()}): {input_file.name}[/yellow]")
                    skipped_count += 1
                    progress.update(overall_task, advance=1)
                    continue

                # Convert file
                output_file = self._get_output_filename(input_file, target_format)
                progress.console.print(f"[{i+1}/{len(valid_files)}] {input_file.name} → {output_file.name}")

                if self._convert_file(input_file, output_file, target_format):
                    success_count += 1
                    progress.console.print(f"[green]✓ Success[/green]")
                else:
                    failed_count += 1
                    progress.console.print(f"[red]✗ Failed[/red]")

                progress.update(overall_task, advance=1)

        # Summary
        self.console.print(f"\n[bold]Conversion Summary:[/bold]")
        self.console.print(f"[green]Successful: {success_count}[/green]")
        self.console.print(f"[red]Failed: {failed_count}[/red]")
        self.console.print(f"[yellow]Skipped: {skipped_count}[/yellow]")

        return {'success': success_count, 'failed': failed_count, 'skipped': skipped_count}