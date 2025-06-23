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
    
    def get_audio_metadata(self, file_path: Path) -> Dict[str, str]:
        """Get basic audio metadata (artist, title, etc.)"""
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
                    
        except Exception as e:
            logger.warning(f"Could not read metadata from {file_path}: {e}")
        
        return metadata
    
    def display_file_info(self, file_path: Path) -> None:
        """Display file information in two tables: metadata and custom tags"""
        self.console.print(f"\n[bold blue]File: {file_path.name}[/bold blue]")
        
        # Get basic metadata
        metadata = self.get_audio_metadata(file_path)
        if metadata:
            metadata_table = Table(title="Basic Metadata", box=box.ROUNDED, show_lines=True)
            metadata_table.add_column("Field", style="cyan", no_wrap=True)
            metadata_table.add_column("Value", style="green")
            
            for key, value in metadata.items():
                metadata_table.add_row(key.title(), value)
            
            self.console.print(metadata_table)
        else:
            self.console.print("\n[yellow]No basic metadata found.[/yellow]")
        
        # Get existing TXXX tags
        existing_tags = self.get_file_tags(file_path)
        if existing_tags:
            tags_table = Table(title="Custom Tags", box=box.ROUNDED, show_lines=True)
            tags_table.add_column("Category", style="cyan", no_wrap=True)
            tags_table.add_column("Values", style="green")
            
            for category, values in existing_tags.items():
                tags_table.add_row(category, ", ".join(values))
            
            self.console.print(tags_table)
        else:
            self.console.print("\n[yellow]No custom tags found.[/yellow]")
    
    def add_tag_to_file(self, file_path: Path, category: str, value: str) -> bool:
        """Add a value to a TXXX tag in a music file"""
        try:
            # Use specific file type handling for better compatibility
            if file_path.suffix.lower() == '.mp3':
                audio = File(str(file_path))
                if audio is None:
                    return False
                
                # Ensure tags exist for MP3
                if not hasattr(audio, 'tags') or audio.tags is None:
                    audio.tags = ID3()
            else:
                # For AIFF and other formats, use the generic File approach
                audio = File(str(file_path))
                if audio is None:
                    return False
                
                # Ensure tags exist for other formats
                if not hasattr(audio, 'tags') or audio.tags is None:
                    audio.add_tags()
            
            txxx_key = f'TXXX:{category.upper()}'
            
            # Check if the category already exists
            existing_values = []
            
            # Use file extension to determine format instead of checking methods
            if file_path.suffix.lower() == '.mp3':
                # MP3 files - get all existing values
                if hasattr(audio.tags, 'getall'):
                    existing_frames = audio.tags.getall(txxx_key)
                    for frame in existing_frames:
                        if hasattr(frame, 'text'):
                            existing_values.extend(frame.text)
            else:
                # AIFF and other formats - get values from single frame
                try:
                    existing_frame = audio.tags[txxx_key]
                    if hasattr(existing_frame, 'text'):
                        existing_values.extend(existing_frame.text)
                except KeyError:
                    pass  # Category doesn't exist yet
            
            # Check if value already exists
            if value in existing_values:
                logger.info(f"Value '{value}' already exists in category '{category}'")
                return True  # Not an error, just already exists
            
            # Add the new value
            if file_path.suffix.lower() == '.mp3':
                # MP3 files - add new frame
                audio.tags.add(TXXX(encoding=3, desc=category.upper(), text=value))
            else:
                # AIFF and other formats - update existing frame or create new one
                if existing_values:
                    # Update existing frame with all values as comma-separated string
                    all_values = existing_values + [value]
                    # Join with commas and spaces for readability
                    combined_text = ", ".join(all_values)
                    audio.tags[txxx_key] = TXXX(encoding=3, desc=category.upper(), text=combined_text)
                else:
                    # Create new frame
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
    
    def display_categories(self, categories: List[str], selected_index: int) -> None:
        """Display categories with arrow key navigation"""
        self.console.print("\n[bold cyan]Tag Categories:[/bold cyan]")
        self.console.print("Use ↑/↓ to navigate, Enter/→ to select, q to quit")
        
        for i, category in enumerate(categories):
            if i == selected_index:
                self.console.print(f"  [bold green]▶ {category}[/bold green]")
            else:
                self.console.print(f"    {category}")
    
    def display_values(self, category: str, values: List[str], selected_values: set, selected_index: int) -> None:
        """Display values with checkbox-style selection"""
        self.console.print(f"\n[bold green]Values for '{category}':[/bold green]")
        self.console.print("Use ↑/↓ to navigate, Space to toggle, Enter to save, ← to go back")
        
        for i, value in enumerate(values):
            is_selected = value in selected_values
            is_highlighted = i == selected_index
            
            if is_selected:
                checkbox = "[green]✓[/green]"
            else:
                checkbox = "[red]✗[/red]"
            
            if is_highlighted:
                self.console.print(f"  [bold green]▶ {checkbox} {value}[/bold green]")
            else:
                self.console.print(f"    {checkbox} {value}")
    
    def get_key_press(self) -> str:
        """Get a single key press, handling arrow keys and special characters"""
        try:
            # For Unix-like systems
            import tty
            import termios
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
                
                # Check for escape sequences (arrow keys)
                if ch == '\x1b':
                    next_ch = sys.stdin.read(1)
                    if next_ch == '[':
                        third_ch = sys.stdin.read(1)
                        if third_ch == 'A':
                            return 'up'
                        elif third_ch == 'B':
                            return 'down'
                        elif third_ch == 'C':
                            return 'right'
                        elif third_ch == 'D':
                            return 'left'
                
                return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except (ImportError, AttributeError):
            # For Windows systems
            try:
                import msvcrt
                ch = msvcrt.getch().decode('utf-8')
                
                # Handle Windows arrow keys
                if ch == '\xe0':
                    next_ch = msvcrt.getch().decode('utf-8')
                    if next_ch == 'H':
                        return 'up'
                    elif next_ch == 'P':
                        return 'down'
                    elif next_ch == 'M':
                        return 'right'
                    elif next_ch == 'K':
                        return 'left'
                
                return ch
            except:
                # Fallback to simple input
                return input()
    
    def edit_category_values(self, file_path: Path, category: str) -> None:
        """Edit values for a specific category with checkbox-style selection"""
        values = self.schema[category]
        if not values:
            self.console.print(f"[yellow]No values defined for category '{category}'[/yellow]")
            return
        
        # Get current values for this category
        current_tags = self.get_file_tags(file_path)
        current_values = set(current_tags.get(category, []))
        
        selected_index = 0
        
        while True:
            self.console.clear()
            self.display_file_info(file_path)
            self.display_values(category, values, current_values, selected_index)
            
            key = self.get_key_press()
            
            if key == 'left':
                break  # Go back to categories
            elif key == 'up':
                selected_index = max(0, selected_index - 1)
            elif key == 'down':
                selected_index = min(len(values) - 1, selected_index + 1)
            elif key == ' ':  # Space to toggle
                value = values[selected_index]
                if value in current_values:
                    # Remove the value
                    if self.remove_tag_from_file(file_path, category, value):
                        current_values.remove(value)
                        self.console.print(f"[green]Removed: {category} = {value}[/green]")
                    else:
                        self.console.print(f"[red]Failed to remove: {category} = {value}[/red]")
                else:
                    # Add the value
                    if self.add_tag_to_file(file_path, category, value):
                        current_values.add(value)
                        self.console.print(f"[green]Added: {category} = {value}[/green]")
                    else:
                        self.console.print(f"[red]Failed to add: {category} = {value}[/red]")
                
                # Brief pause to show the message
                import time
                time.sleep(0.5)
            elif key == 'enter':
                # Save and go back
                break
    
    def edit_file_tags_enhanced(self, file_path: Path) -> None:
        """Enhanced interactive tag editing with arrow key navigation"""
        categories = list(self.schema.keys())
        if not categories:
            self.console.print("[red]No tag categories found in schema![/red]")
            return
        
        selected_category_index = 0
        
        while True:
            self.console.clear()
            self.display_file_info(file_path)
            self.display_categories(categories, selected_category_index)
            
            key = self.get_key_press()
            
            if key.lower() == 'q':
                break
            elif key == 'up':
                selected_category_index = max(0, selected_category_index - 1)
            elif key == 'down':
                selected_category_index = min(len(categories) - 1, selected_category_index + 1)
            elif key in ['enter', 'right']:
                # Enter the selected category
                selected_category = categories[selected_category_index]
                self.edit_category_values(file_path, selected_category)
    
    def tag_single_file(self, file_path: Path) -> None:
        """Main entry point for enhanced single file tagging"""
        if not file_path.exists():
            self.console.print(f"[red]File not found: {file_path}[/red]")
            return
        
        self.console.print(f"[green]Tagging file: {file_path.name}[/green]")
        self.edit_file_tags_enhanced(file_path)
        self.console.print("[green]Tagging completed![/green]")
    
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
                self.tag_single_file(selected_file)
        
        self.console.print("[green]Tagging session completed![/green]")