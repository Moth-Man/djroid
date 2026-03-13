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
from dj_en.logging import get_logger
from mutagen import File
from mutagen.id3 import ID3, TXXX
from mutagen.aiff import AIFF
import os
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Header, Footer, Static, Button
from textual.widgets.data_table import RowKey
from textual import work
from textual.reactive import reactive

logger = get_logger(__name__)

class FileSelectorApp(App):
    """Interactive file selector using Textual"""
    
    CSS = """
    DataTable {
        height: 70%;
    }
    
    .file-info {
        height: 30%;
        border: solid green;
    }
    
    .selected {
        background: $accent;
    }
    """
    
    def __init__(self, files: List[Path], schema: Dict[str, List[str]]):
        super().__init__()
        self.files = files
        self.schema = schema
        self.selected_file = None
        
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield DataTable()
        yield Static("File information will appear here", classes="file-info")
        yield Footer()
    
    def on_mount(self) -> None:
        """Set up the data table when the app starts."""
        table = self.query_one(DataTable)
        table.add_columns("Filename", "Size", "Type")
        
        for file_path in self.files:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            file_type = file_path.suffix.upper()
            table.add_row(
                file_path.name,
                f"{size_mb:.1f} MB",
                file_type,
                key=str(file_path)
            )
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        if event.row_key:
            file_path = Path(event.row_key.value)
            self.selected_file = file_path
            self.update_file_info(file_path)
    
    def update_file_info(self, file_path: Path) -> None:
        """Update the file information display."""
        info_widget = self.query_one(".file-info")
        
        # Get basic metadata
        metadata = self.get_audio_metadata(file_path)
        existing_tags = self.get_file_tags(file_path)
        
        info_text = f"File: {file_path.name}\n\n"
        
        if metadata:
            info_text += "Basic Metadata:\n"
            for key, value in metadata.items():
                info_text += f"  {key.title()}: {value}\n"
        
        if existing_tags:
            info_text += "\nExisting Custom Tags:\n"
            for category, values in existing_tags.items():
                info_text += f"  {category}: {', '.join(values)}\n"
        else:
            info_text += "\nNo custom tags found."
        
        info_widget.update(info_text)
    
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

    def on_key(self, event) -> None:
        """Handle keyboard events."""
        if event.key == "enter":
            if self.selected_file:
                # Exit the app and continue with tag editing
                self.exit()
        elif event.key == "escape":
            # Exit without selecting
            self.selected_file = None
            self.exit()

class TagInteractive:
    """
    Enhanced interactive tagging interface using Textual TUI.

    Provides a file selector app and rich interactive tagging experience
    with schema-based tag management, metadata editing, and visual feedback.
    """

    def __init__(self):
        """Initialize TagInteractive with console output and schema loading."""
        self.console = Console()
        self.schema_file = Path.home() / '.dj-en' / 'tag_schema.json'
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
    
    def run_interactive_selector(self, directory: Path):
        """Run the interactive file selector"""
        music_files = self.find_music_files(directory)
        
        if not music_files:
            self.console.print("[red]No music files found in the current directory![/red]")
            return
        
        self.console.print(f"[green]Found {len(music_files)} music files.[/green]")
        self.console.print("Starting interactive file selector...")
        
        # Run the Textual app
        app = FileSelectorApp(music_files, self.schema)
        app.run()
        
        # After the app closes, we can continue with tag editing
        if app.selected_file:
            self.edit_file_tags_interactive(app.selected_file)
    
    def edit_file_tags_interactive(self, file_path: Path):
        """Interactive tag editing with rich interface"""
        while True:
            self.console.clear()
            
            # Display file info
            self.display_file_info(file_path)
            
            # Show available actions
            self.console.print("\n[bold green]Available Actions:[/bold green]")
            self.console.print("  1. Add tags")
            self.console.print("  2. Remove tags")
            self.console.print("  3. View schema")
            self.console.print("  4. Back to file list")
            
            choice = Prompt.ask("Choose action", choices=["1", "2", "3", "4"], default="4")
            
            if choice == "1":
                self.add_tags_to_file_interactive(file_path)
            elif choice == "2":
                self.remove_tags_from_file_interactive(file_path)
            elif choice == "3":
                self.display_schema_table()
                Prompt.ask("Press Enter to continue")
            elif choice == "4":
                break
    
    def display_file_info(self, file_path: Path):
        """Display comprehensive file information"""
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
    
    def display_schema_table(self):
        """Display the current schema in a table"""
        table = Table(title="Current Tag Schema", box=box.ROUNDED, show_lines=True)
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Values", style="green")
        table.add_column("Count", style="yellow", justify="center")
        
        for category, values in self.schema.items():
            values_str = ", ".join(values) if values else "(empty)"
            count = len(values)
            table.add_row(category, values_str, str(count))
        
        self.console.print(table)
    
    def add_tags_to_file_interactive(self, file_path: Path):
        """Interactive tag addition"""
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
    
    def remove_tags_from_file_interactive(self, file_path: Path):
        """Interactive tag removal"""
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