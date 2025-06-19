import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.text import Text
from rich import box
import click
from djroid.logging import get_logger
from mutagen import File
from mutagen.id3 import ID3, TXXX
from mutagen.aiff import AIFF
import os

logger = get_logger(__name__)

class Tag:
    def __init__(self):
        self.console = Console()
        self.schema_file = Path.home() / '.djroid' / 'tag_schema.json'
        self.schema: Dict[str, List[str]] = self.load_schema()
        
    def load_schema(self) -> Dict[str, List[str]]:
        """Load existing schema from file"""
        if self.schema_file.exists():
            with open(self.schema_file, 'r') as f:
                return json.load(f)
        logger.error(f"Tag schema file not found at {self.schema_file}")
        self.console.print("[red]Error: Tag schema not found![/red]")
        self.console.print("Please run 'tag-schema' first to set up your tagging categories.")
        sys.exit(1)
    
    def find_music_files(self, directory: Path) -> List[Path]:
        """Find all music files in the given directory"""
        music_extensions = {'.mp3', '.aiff', '.wav', '.flac', '.m4a', '.ogg'}
        music_files = []
        
        for ext in music_extensions:
            music_files.extend(directory.glob(f'*{ext}'))
        
        return sorted(music_files)
    
    def display_file_table(self, files: List[Path], selected_index: int = 0) -> None:
        """Display files in a table with selection highlighting"""
        table = Table(title="Music Files", box=box.ROUNDED, show_lines=True)
        table.add_column("#", style="cyan", justify="center")
        table.add_column("Filename", style="green")
        table.add_column("Size", style="yellow", justify="right")
        table.add_column("Type", style="blue")
        
        for i, file_path in enumerate(files):
            size_mb = file_path.stat().st_size / (1024 * 1024)
            file_type = file_path.suffix.upper()
            
            # Highlight selected row
            if i == selected_index:
                table.add_row(
                    f"[bold cyan]{i+1}[/bold cyan]",
                    f"[bold green]{file_path.name}[/bold green]",
                    f"[bold yellow]{size_mb:.1f} MB[/bold yellow]",
                    f"[bold blue]{file_type}[/bold blue]"
                )
            else:
                table.add_row(
                    str(i+1),
                    file_path.name,
                    f"{size_mb:.1f} MB",
                    file_type
                )
        
        self.console.print(table)
    
    def get_file_tags(self, file_path: Path) -> Dict[str, List[str]]:
        """Get existing TXXX tags from a music file"""
        tags = {}
        
        try:
            audio = File(str(file_path))
            
            if audio is None:
                return tags
            
            # Handle MP3 files
            if hasattr(audio, 'tags') and audio.tags:
                if hasattr(audio.tags, 'getall'):
                    for key in audio.tags.keys():
                        if key.startswith('TXXX:'):
                            category = key[5:]  # Remove 'TXXX:' prefix
                            values = audio.tags.getall(key)
                            tags[category] = [str(v) for v in values]
            
            # Handle AIFF files
            elif hasattr(audio, 'tags'):
                for key, value in audio.tags.items():
                    if key.startswith('TXXX:'):
                        category = key[5:]
                        if category not in tags:
                            tags[category] = []
                        tags[category].append(str(value))
                        
        except Exception as e:
            logger.warning(f"Could not read tags from {file_path}: {e}")
        
        return tags
    
    def get_audio_metadata(self, file_path: Path) -> Dict[str, str]:
        """Get basic audio metadata (artist, title, etc.)"""
        metadata = {}
        
        try:
            audio = File(str(file_path))
            
            if audio is None:
                return metadata
            
            # Common metadata fields
            common_fields = ['title', 'artist', 'album', 'date', 'genre', 'bpm', 'key']
            
            for field in common_fields:
                if hasattr(audio, field) and getattr(audio, field):
                    metadata[field] = str(getattr(audio, field)[0])
                elif hasattr(audio, 'tags') and audio.tags:
                    # Try to get from tags
                    if hasattr(audio.tags, 'get'):
                        value = audio.tags.get(field.upper())
                        if value:
                            metadata[field] = str(value)
                        
        except Exception as e:
            logger.warning(f"Could not read metadata from {file_path}: {e}")
        
        return metadata
    
    def display_file_info(self, file_path: Path) -> None:
        """Display file information and existing tags"""
        self.console.print(f"\n[bold blue]File: {file_path.name}[/bold blue]")
        
        # Get basic metadata
        metadata = self.get_audio_metadata(file_path)
        if metadata:
            self.console.print("\n[bold cyan]Basic Metadata:[/bold cyan]")
            for key, value in metadata.items():
                self.console.print(f"  {key.title()}: {value}")
        
        # Get existing TXXX tags
        existing_tags = self.get_file_tags(file_path)
        if existing_tags:
            self.console.print("\n[bold cyan]Existing Custom Tags:[/bold cyan]")
            for category, values in existing_tags.items():
                self.console.print(f"  {category}: {', '.join(values)}")
        else:
            self.console.print("\n[yellow]No custom tags found.[/yellow]")
    
    def add_tag_to_file(self, file_path: Path, category: str, value: str) -> bool:
        """Add a TXXX tag to a music file"""
        try:
            audio = File(str(file_path))
            
            if audio is None:
                return False
            
            # Ensure tags exist
            if not hasattr(audio, 'tags') or audio.tags is None:
                if file_path.suffix.lower() == '.mp3':
                    audio.tags = ID3()
                # For other formats, we might need different handling
            
            # Add TXXX tag
            txxx_key = f'TXXX:{category.upper()}'
            
            if hasattr(audio.tags, 'add'):
                audio.tags.add(TXXX(encoding=3, desc=category.upper(), text=value))
            elif hasattr(audio.tags, '__setitem__'):
                audio.tags[txxx_key] = TXXX(encoding=3, desc=category.upper(), text=value)
            
            # Save the file
            audio.save()
            return True
            
        except Exception as e:
            logger.error(f"Failed to add tag to {file_path}: {e}")
            return False
    
    def remove_tag_from_file(self, file_path: Path, category: str, value: str = None) -> bool:
        """Remove a TXXX tag from a music file"""
        try:
            audio = File(str(file_path))
            
            if audio is None or not hasattr(audio, 'tags') or audio.tags is None:
                return False
            
            txxx_key = f'TXXX:{category.upper()}'
            
            if value is None:
                # Remove entire category
                if hasattr(audio.tags, '__delitem__'):
                    del audio.tags[txxx_key]
                elif hasattr(audio.tags, 'delete'):
                    audio.tags.delete(txxx_key)
            else:
                # Remove specific value (this is more complex and format-dependent)
                # For now, we'll remove the entire category
                if hasattr(audio.tags, '__delitem__'):
                    del audio.tags[txxx_key]
                elif hasattr(audio.tags, 'delete'):
                    audio.tags.delete(txxx_key)
            
            audio.save()
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove tag from {file_path}: {e}")
            return False
    
    def edit_file_tags(self, file_path: Path) -> None:
        """Interactive tag editing for a single file"""
        while True:
            self.console.clear()
            self.display_file_info(file_path)
            
            # Show available schema categories
            self.console.print(f"\n[bold green]Available Categories:[/bold green]")
            for i, category in enumerate(self.schema.keys(), 1):
                self.console.print(f"  {i}. {category}")
            
            action = Prompt.ask(
                "\nChoose action",
                choices=["add", "remove", "back"],
                default="back"
            )
            
            if action == "back":
                break
            elif action == "add":
                self.add_tags_to_file(file_path)
            elif action == "remove":
                self.remove_tags_from_file(file_path)
    
    def add_tags_to_file(self, file_path: Path) -> None:
        """Add tags to a file"""
        # Select category
        categories = list(self.schema.keys())
        self.console.print("\n[bold cyan]Select category:[/bold cyan]")
        for i, category in enumerate(categories, 1):
            self.console.print(f"  {i}. {category}")
        
        try:
            choice = IntPrompt.ask("Enter category number", default=1)
            if 1 <= choice <= len(categories):
                category = categories[choice - 1]
            else:
                self.console.print("[red]Invalid choice![/red]")
                return
        except ValueError:
            self.console.print("[red]Please enter a valid number![/red]")
            return
        
        # Show available values
        values = self.schema[category]
        self.console.print(f"\n[bold green]Available values for '{category}':[/bold green]")
        for i, value in enumerate(values, 1):
            self.console.print(f"  {i}. {value}")
        
        try:
            choice = IntPrompt.ask("Enter value number", default=1)
            if 1 <= choice <= len(values):
                value = values[choice - 1]
            else:
                self.console.print("[red]Invalid choice![/red]")
                return
        except ValueError:
            self.console.print("[red]Please enter a valid number![/red]")
            return
        
        # Add the tag
        if self.add_tag_to_file(file_path, category, value):
            self.console.print(f"[green]Added tag: {category} = {value}[/green]")
        else:
            self.console.print("[red]Failed to add tag![/red]")
    
    def remove_tags_from_file(self, file_path: Path) -> None:
        """Remove tags from a file"""
        existing_tags = self.get_file_tags(file_path)
        
        if not existing_tags:
            self.console.print("[yellow]No custom tags to remove![/yellow]")
            return
        
        # Show existing tags
        self.console.print("\n[bold red]Existing tags:[/bold red]")
        tag_list = []
        for category, values in existing_tags.items():
            for value in values:
                tag_list.append((category, value))
        
        for i, (category, value) in enumerate(tag_list, 1):
            self.console.print(f"  {i}. {category} = {value}")
        
        try:
            choice = IntPrompt.ask("Enter tag number to remove", default=1)
            if 1 <= choice <= len(tag_list):
                category, value = tag_list[choice - 1]
            else:
                self.console.print("[red]Invalid choice![/red]")
                return
        except ValueError:
            self.console.print("[red]Please enter a valid number![/red]")
            return
        
        # Confirm removal
        if Confirm.ask(f"Remove tag '{category} = {value}'?"):
            if self.remove_tag_from_file(file_path, category, value):
                self.console.print(f"[green]Removed tag: {category} = {value}[/green]")
            else:
                self.console.print("[red]Failed to remove tag![/red]")
    
    def tag_songs(self, directory: Optional[Path] = None):
        """Main tagging interface"""
        if directory is None:
            directory = Path.cwd()
        
        # Find music files
        music_files = self.find_music_files(directory)
        
        if not music_files:
            self.console.print("[red]No music files found in the current directory![/red]")
            return
        
        self.console.print(f"[green]Found {len(music_files)} music files.[/green]")
        
        # Simple file selection (we'll implement arrow key navigation later)
        selected_index = 0
        
        while True:
            self.console.clear()
            self.display_file_table(music_files, selected_index)
            
            self.console.print("\n[bold]Navigation:[/bold]")
            self.console.print("  [j/k] - Move up/down")
            self.console.print("  [Enter] - Select file")
            self.console.print("  [q] - Quit")
            
            key = Prompt.ask("\nAction", default="")
            
            if key.lower() == 'q':
                break
            elif key.lower() == 'j':
                selected_index = min(selected_index + 1, len(music_files) - 1)
            elif key.lower() == 'k':
                selected_index = max(selected_index - 1, 0)
            elif key == '' or key.lower() == 'enter':
                # Edit the selected file
                selected_file = music_files[selected_index]
                self.edit_file_tags(selected_file)
        
        self.console.print("[green]Tagging session completed![/green]")