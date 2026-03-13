"""Service for migrating music files to directories based on metadata rules."""

import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import box
from mutagen import File
from djroid.logging import get_logger
from djroid.db.session import SessionLocal
from djroid.db.dao.migration_rule_dao import MigrationRuleDAO
from djroid.db.dao.song_dao import SongDAO
from djroid.db.models.migration_rule import MigrationRule

logger = get_logger(__name__)


class Migrate:
    """
    Service for migrating music files based on metadata-based rules.

    Reads file metadata, matches against configured rules, and moves
    files to their designated destination directories.
    """

    SUPPORTED_EXTENSIONS = {'.mp3', '.aiff', '.wav', '.flac', '.m4a', '.ogg', '.aac'}

    def __init__(self):
        """Initialize Migrate service with console output."""
        self.console = Console()

    def find_music_files(self, directory: Path) -> List[Path]:
        """Find all music files in the given directory recursively."""
        music_files = []

        logger.info(f"Scanning directory for music files: {directory}")

        for ext in self.SUPPORTED_EXTENSIONS:
            music_files.extend(directory.rglob(f'*{ext}'))

        return sorted(music_files)

    def get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from a music file using mutagen.

        Args:
            file_path: Path to the music file

        Returns:
            Dictionary of metadata fields
        """
        metadata = {}

        try:
            audio = File(str(file_path))

            if audio is None:
                return metadata

            if not hasattr(audio, 'tags') or audio.tags is None:
                return metadata

            # Metadata fields with their tag keys
            tag_mappings = {
                'title': ['TIT2', 'TITLE', 'title'],
                'artist': ['TPE1', 'ARTIST', 'artist'],
                'album': ['TALB', 'ALBUM', 'album'],
                'genre': ['TCON', 'GENRE', 'genre'],
                'bpm': ['TBPM', 'BPM', 'bpm'],
                'key': ['TKEY', 'KEY', 'key'],
                'year': ['TDRC', 'DATE', 'date', 'year'],
                'publisher': ['TPUB', 'PUBLISHER', 'publisher'],
            }

            for field, possible_keys in tag_mappings.items():
                for key in possible_keys:
                    try:
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

            # Convert BPM to string for matching
            if 'bpm' in metadata:
                try:
                    bpm_float = float(metadata['bpm'])
                    metadata['bpm'] = str(int(bpm_float))
                except (ValueError, TypeError):
                    pass

            # Extract year from date fields
            if 'year' in metadata:
                try:
                    year_str = metadata['year']
                    if year_str and len(year_str) >= 4:
                        metadata['year'] = year_str[:4]
                except (ValueError, TypeError):
                    pass

        except Exception as e:
            logger.warning(f"Could not read metadata from {file_path}: {e}")

        return metadata

    def find_matching_rule(
        self,
        metadata: Dict[str, Any],
        rules: List[MigrationRule]
    ) -> Optional[MigrationRule]:
        """Find the first matching migration rule for a file's metadata.

        Args:
            metadata: Dictionary of file metadata
            rules: List of migration rules to check

        Returns:
            The first matching rule, or None if no match
        """
        for rule in rules:
            tag_name = rule.metadata_tag.lower()
            tag_value = metadata.get(tag_name, "")

            if tag_value and tag_value.lower() == rule.metadata_value.lower():
                return rule

        return None

    def move_file(
        self,
        source: Path,
        destination_dir: Path,
        dry_run: bool = False
    ) -> Tuple[bool, Optional[Path]]:
        """Move a file to the destination directory.

        Args:
            source: Source file path
            destination_dir: Target directory
            dry_run: If True, don't actually move the file

        Returns:
            Tuple of (success, new_path or None)
        """
        try:
            # Ensure destination directory exists
            if not dry_run:
                destination_dir.mkdir(parents=True, exist_ok=True)

            # Build destination path
            destination = destination_dir / source.name

            # Handle name collision
            if destination.exists():
                counter = 1
                stem = source.stem
                suffix = source.suffix
                while destination.exists():
                    destination = destination_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

            if not dry_run:
                shutil.move(str(source), str(destination))
                logger.info(f"Moved {source} -> {destination}")

            return True, destination

        except Exception as e:
            logger.error(f"Failed to move {source}: {e}")
            return False, None

    def update_database_filepath(
        self,
        old_path: str,
        new_path: str
    ) -> bool:
        """Update the filepath in the database after moving a file.

        Args:
            old_path: Original file path
            new_path: New file path

        Returns:
            True if database was updated, False otherwise
        """
        try:
            db = SessionLocal()
            try:
                song_dao = SongDAO(db)
                song = song_dao.get_by_filepath(old_path)
                if song:
                    song.filepath = new_path
                    db.commit()
                    logger.info(f"Updated database filepath: {old_path} -> {new_path}")
                    return True
                return False
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to update database filepath: {e}")
            return False

    def migrate_directory(
        self,
        directory: Path,
        dry_run: bool = False,
        show_progress: bool = True
    ) -> Dict[str, int]:
        """Migrate all music files in a directory based on configured rules.

        Args:
            directory: Directory to scan for music files
            dry_run: If True, only show what would be done without moving
            show_progress: Show progress bar

        Returns:
            Dictionary with counts: success, failed, skipped, no_match
        """
        results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'no_match': 0
        }

        # Load rules from database
        db = SessionLocal()
        try:
            rule_dao = MigrationRuleDAO(db)
            rules = rule_dao.get_all_rules(enabled_only=True)

            if not rules:
                self.console.print("[yellow]No migration rules configured.[/yellow]")
                self.console.print("Use the TUI settings to create migration rules.")
                return results

            self.console.print(f"\n[bold]Loaded {len(rules)} migration rules[/bold]")

            # Display rules summary
            rules_table = Table(box=box.SIMPLE, show_header=True)
            rules_table.add_column("Tag", style="cyan")
            rules_table.add_column("Value", style="green")
            rules_table.add_column("Destination", style="blue")

            for rule in rules:
                rules_table.add_row(
                    rule.metadata_tag,
                    rule.metadata_value,
                    rule.destination_directory
                )

            self.console.print(rules_table)

        finally:
            db.close()

        # Find music files
        music_files = self.find_music_files(directory)

        if not music_files:
            self.console.print("[yellow]No music files found in directory.[/yellow]")
            return results

        self.console.print(f"\n[bold]Found {len(music_files)} music files[/bold]")

        if dry_run:
            self.console.print("[yellow][DRY RUN] No files will be moved[/yellow]\n")

        # Process files
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            disable=not show_progress
        ) as progress:

            task = progress.add_task("Migrating files...", total=len(music_files))

            for file_path in music_files:
                # Read metadata
                metadata = self.get_file_metadata(file_path)

                if not metadata:
                    progress.console.print(
                        f"[dim]Skipped (no metadata): {file_path.name}[/dim]"
                    )
                    results['skipped'] += 1
                    progress.update(task, advance=1)
                    continue

                # Find matching rule
                rule = self.find_matching_rule(metadata, rules)

                if not rule:
                    progress.console.print(
                        f"[dim]No matching rule: {file_path.name}[/dim]"
                    )
                    results['no_match'] += 1
                    progress.update(task, advance=1)
                    continue

                # Move file
                dest_dir = Path(rule.destination_directory)
                success, new_path = self.move_file(file_path, dest_dir, dry_run=dry_run)

                if success:
                    if dry_run:
                        progress.console.print(
                            f"[cyan]Would move:[/cyan] {file_path.name} -> {dest_dir}"
                        )
                    else:
                        progress.console.print(
                            f"[green]Moved:[/green] {file_path.name} -> {dest_dir}"
                        )

                        # Update database if file was tracked
                        if new_path:
                            self.update_database_filepath(
                                str(file_path),
                                str(new_path)
                            )

                    results['success'] += 1
                else:
                    progress.console.print(
                        f"[red]Failed:[/red] {file_path.name}"
                    )
                    results['failed'] += 1

                progress.update(task, advance=1)

        # Summary
        self.console.print(f"\n[bold]Migration Summary:[/bold]")
        self.console.print(f"[green]Moved: {results['success']}[/green]")
        self.console.print(f"[red]Failed: {results['failed']}[/red]")
        self.console.print(f"[yellow]Skipped: {results['skipped']}[/yellow]")
        self.console.print(f"[dim]No matching rule: {results['no_match']}[/dim]")

        return results

    def migrate_single_file(
        self,
        file_path: Path,
        dry_run: bool = False
    ) -> bool:
        """Migrate a single file based on configured rules.

        Args:
            file_path: Path to the music file
            dry_run: If True, only show what would be done

        Returns:
            True if file was migrated (or would be in dry run), False otherwise
        """
        if not file_path.exists():
            self.console.print(f"[red]Error: File not found: {file_path}[/red]")
            return False

        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            self.console.print(f"[red]Error: Not a supported audio file: {file_path}[/red]")
            return False

        # Load rules
        db = SessionLocal()
        try:
            rule_dao = MigrationRuleDAO(db)
            rules = rule_dao.get_all_rules(enabled_only=True)

            if not rules:
                self.console.print("[yellow]No migration rules configured.[/yellow]")
                return False

        finally:
            db.close()

        # Read metadata
        metadata = self.get_file_metadata(file_path)

        if not metadata:
            self.console.print(f"[yellow]No metadata found in file[/yellow]")
            return False

        # Display metadata
        self.console.print(f"\n[bold]File metadata:[/bold]")
        for key, value in metadata.items():
            self.console.print(f"  {key}: {value}")

        # Find matching rule
        rule = self.find_matching_rule(metadata, rules)

        if not rule:
            self.console.print(f"\n[yellow]No matching migration rule found[/yellow]")
            return False

        self.console.print(f"\n[bold]Matching rule:[/bold]")
        self.console.print(f"  {rule.metadata_tag}: {rule.metadata_value}")
        self.console.print(f"  Destination: {rule.destination_directory}")

        # Move file
        dest_dir = Path(rule.destination_directory)
        success, new_path = self.move_file(file_path, dest_dir, dry_run=dry_run)

        if success:
            if dry_run:
                self.console.print(f"\n[cyan]Would move to: {dest_dir}[/cyan]")
            else:
                self.console.print(f"\n[green]Moved to: {new_path}[/green]")

                # Update database
                if new_path:
                    self.update_database_filepath(str(file_path), str(new_path))

        return success
