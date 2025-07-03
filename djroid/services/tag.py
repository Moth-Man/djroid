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
        self.current_file: Optional[Path] = None
        
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
                    
        except Exception as e:
            logger.warning(f"Could not read metadata from {file_path}: {e}")
        
        return metadata
    
    def display_file_info(self, file_path: Path) -> None:
        """Display file information in two tables: metadata and custom tags"""
        self.console.print(f"\n[bold blue]File: {file_path.name}[/bold blue]")
        
        # Get basic metadata
        metadata = self.get_audio_metadata(file_path)
        
        # Get Rekordbox comment separately for special handling
        rekordbox_comment = self.get_rekordbox_comment(file_path)
        
        if metadata or rekordbox_comment:
            metadata_table = Table(title="Basic Metadata", box=box.ROUNDED, show_lines=True)
            metadata_table.add_column("Field", style="cyan", no_wrap=True)
            metadata_table.add_column("Value", style="green")
            
            # Add regular metadata fields
            for key, value in metadata.items():
                if key != 'comment':  # Skip generic comment, we'll handle Rekordbox comment separately
                    metadata_table.add_row(key.title(), value)
            
            # Add Rekordbox comment with special styling
            if rekordbox_comment:
                metadata_table.add_row("[bold yellow]Comment[/bold yellow]", rekordbox_comment)
            
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
            # Initialize audio variable
            audio = None
            
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
            
            # Ensure audio is properly initialized
            if audio is None:
                logger.error(f"Failed to initialize audio object for {file_path}")
                return False
            
            txxx_key = f'TXXX:{category.upper()}'
            
            # Check if the category already exists and get existing values
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
                        # Handle both list and string formats - use same logic as get_file_tags
                        text_values = existing_frame.text
                        if isinstance(text_values, list):
                            # If it's already a list, split each item by commas
                            for item in text_values:
                                if isinstance(item, str):
                                    # Split by commas and strip whitespace
                                    split_values = [v.strip() for v in item.split(',') if v.strip()]
                                    existing_values.extend(split_values)
                                else:
                                    existing_values.append(str(item))
                        else:
                            # If it's a string, split by commas and strip whitespace
                            existing_values = [v.strip() for v in str(text_values).split(',') if v.strip()]
                except KeyError:
                    pass  # Category doesn't exist yet
            
            # Check if value already exists (case-insensitive)
            # Also check for exact matches and trimmed whitespace
            value_normalized = value.strip().lower()
            existing_normalized = [v.strip().lower() for v in existing_values if v.strip()]
            
            if value_normalized in existing_normalized:
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
                elif hasattr(audio.tags, 'delall'):
                    audio.tags.delall(txxx_key)
            else:
                # Remove specific value
                if file_path.suffix.lower() == '.mp3':
                    # MP3 files - remove specific frame
                    if hasattr(audio.tags, 'getall'):
                        existing_frames = audio.tags.getall(txxx_key)
                        frames_to_keep = []
                        for frame in existing_frames:
                            if hasattr(frame, 'text') and value not in frame.text:
                                frames_to_keep.append(frame)
                        
                        # Remove all frames and re-add the ones to keep
                        audio.tags.delall(txxx_key)
                        for frame in frames_to_keep:
                            audio.tags.add(frame)
                else:
                    # AIFF and other formats - update the comma-separated string
                    try:
                        existing_frame = audio.tags[txxx_key]
                        if hasattr(existing_frame, 'text'):
                            # Parse existing values properly - use same logic as add_tag_to_file
                            text_values = existing_frame.text
                            if isinstance(text_values, list):
                                # If it's already a list, split each item by commas
                                existing_values = []
                                for item in text_values:
                                    if isinstance(item, str):
                                        # Split by commas and strip whitespace
                                        split_values = [v.strip() for v in item.split(',') if v.strip()]
                                        existing_values.extend(split_values)
                                    else:
                                        existing_values.append(str(item))
                            else:
                                # If it's a string, split by commas and strip whitespace
                                existing_values = [v.strip() for v in str(text_values).split(',') if v.strip()]
                            
                            # Remove the specific value (case-insensitive)
                            value_to_remove = None
                            for existing_value in existing_values:
                                if existing_value.lower() == value.lower():
                                    value_to_remove = existing_value
                                    break
                            
                            if value_to_remove:
                                existing_values.remove(value_to_remove)
                                
                                # Update or remove the tag
                                if existing_values:
                                    # Update with remaining values
                                    combined_text = ", ".join(existing_values)
                                    audio.tags[txxx_key] = TXXX(encoding=3, desc=category.upper(), text=combined_text)
                                else:
                                    # Remove entire category if no values left
                                    if hasattr(audio.tags, '__delitem__'):
                                        del audio.tags[txxx_key]
                                    elif hasattr(audio.tags, 'delete'):
                                        audio.tags.delete(txxx_key)
                                    elif hasattr(audio.tags, 'delall'):
                                        audio.tags.delall(txxx_key)
                    except KeyError:
                        # Category doesn't exist, nothing to remove
                        pass
            
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
        self.console.print("Press 'd' to delete entire category, 'a' to add new value")
        
        # Create a set of normalized selected values for case-insensitive comparison
        selected_normalized = {v.strip().lower() for v in selected_values if v.strip()}
        
        for i, value in enumerate(values):
            # Check if this value is currently selected (case-insensitive)
            is_selected = value.strip().lower() in selected_normalized
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
        
        # Get current values for this category from the file's TXXX tags
        current_tags = self.get_file_tags(file_path)
        current_values = set()
        
        # Try to get values using the exact category name from schema
        if category in current_tags:
            current_values.update(current_tags[category])
        
        # Also try uppercase version (for consistency with TXXX tags)
        if category.upper() in current_tags:
            current_values.update(current_tags[category.upper()])
        
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
                
                # Check if value is currently selected (case-insensitive)
                is_currently_selected = any(v.strip().lower() == value.strip().lower() for v in current_values)
                
                if is_currently_selected:
                    # Remove the value
                    if self.remove_tag_from_file(file_path, category, value):
                        # Remove the matching value (case-insensitive)
                        value_to_remove = None
                        for v in current_values:
                            if v.strip().lower() == value.strip().lower():
                                value_to_remove = v
                                break
                        if value_to_remove:
                            current_values.remove(value_to_remove)
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
            elif key.lower() == 'a':
                # Add new value to category
                self.add_new_value_to_category(file_path, category, values, current_values)
            elif key.lower() == 'd':
                # Delete entire category with confirmation
                if current_values:
                    self.console.print(f"\n[bold red]Delete entire category '{category}'?[/bold red]")
                    self.console.print(f"This will remove all values: {', '.join(current_values)}")
                    self.console.print("This action cannot be undone.")
                    
                    confirm = input("Are you sure? (y/n): ").strip().lower()
                    
                    if confirm in ['y', 'yes']:
                        if self.remove_tag_from_file(file_path, category):
                            current_values.clear()
                            self.console.print(f"[green]Deleted entire category: {category}[/green]")
                        else:
                            self.console.print(f"[red]Failed to delete category: {category}[/red]")
                    else:
                        self.console.print("[yellow]Category deletion cancelled.[/yellow]")
                else:
                    self.console.print(f"[yellow]Category '{category}' is already empty[/yellow]")
                
                # Brief pause to show the message
                import time
                time.sleep(1)
            elif key == 'enter':
                # Save and go back
                break
    
    def add_new_value_to_category(self, file_path: Path, category: str, values: List[str], current_values: set) -> None:
        """Add a new value to a category on the fly"""
        self.console.print(f"\n[bold cyan]Add New Value to '{category}'[/bold cyan]")
        self.console.print("Enter a new value for this category:")
        
        # Get user input for the new value
        new_value = input("New value: ").strip()
        
        if not new_value:
            self.console.print("[yellow]No value entered. Cancelled.[/yellow]")
            import time
            time.sleep(1)
            return
        
        # Check if value already exists in schema (case-insensitive)
        if new_value.lower() in [v.lower() for v in values]:
            self.console.print(f"[yellow]Value '{new_value}' already exists in the schema![/yellow]")
            import time
            time.sleep(1)
            return
        
        # Confirm with user
        self.console.print(f"\n[bold]Add '{new_value}' to category '{category}'?[/bold]")
        self.console.print("This will:")
        self.console.print(f"  1. Add '{new_value}' to the schema for '{category}'")
        self.console.print(f"  2. Add '{new_value}' to this file's tags")
        
        confirm = input("Continue? (y/n): ").strip().lower()
        
        if confirm not in ['y', 'yes']:
            self.console.print("[yellow]Cancelled.[/yellow]")
            import time
            time.sleep(1)
            return
        
        # Add to schema first
        if self.add_value_to_schema(category, new_value):
            # Add to file
            if self.add_tag_to_file(file_path, category, new_value):
                # Update the current values set (don't modify the values list directly)
                current_values.add(new_value)
                self.console.print(f"[green]Successfully added '{new_value}' to '{category}'![/green]")
            else:
                self.console.print(f"[red]Failed to add '{new_value}' to file, but it was added to schema.[/red]")
        else:
            self.console.print(f"[red]Failed to add '{new_value}' to schema.[/red]")
        
        # Brief pause to show the message
        import time
        time.sleep(1)
    
    def add_value_to_schema(self, category: str, value: str) -> bool:
        """Add a new value to the schema for a category"""
        try:
            if category not in self.schema:
                self.schema[category] = []
            
            # Check if value already exists (case-insensitive)
            if value.strip().lower() in [v.strip().lower() for v in self.schema[category]]:
                logger.info(f"Value '{value}' already exists in schema for category '{category}'")
                return True  # Not an error, just already exists
            
            # Add the new value to the schema
            self.schema[category].append(value)
            
            # Save the updated schema
            self.schema_file.parent.mkdir(exist_ok=True)
            with open(self.schema_file, 'w') as f:
                json.dump(self.schema, f, indent=2)
            
            logger.info(f"Added value '{value}' to schema for category '{category}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add value to schema: {e}")
            return False
    
    def edit_file_tags_enhanced(self, file_path: Path) -> None:
        """Enhanced interactive tag editing with arrow key navigation"""
        # Store the current file for migration reference
        self.current_file = file_path
        
        categories = list(self.schema.keys())
        if not categories:
            self.console.print("[red]No tag categories found in schema! Try running `djroid tag-schema` to create a schema.[/red]")
            return
        
        selected_category_index = 0
        
        while True:
            self.console.clear()
            self.display_file_info(file_path)
            
            # Show main navigation options
            self.console.print("\n[bold cyan]Main Options:[/bold cyan]")
            self.console.print("Use ↑/↓ to navigate, Enter/→ to select, q to quit")
            
            # Show metadata option
            self.console.print("  (m) - Edit Metadata (including Rekordbox Comment)")
            # Show migration option
            self.console.print("  (v) - Migrate File to Different Directory")
            
            # Show tag categories
            self.console.print("\n[bold cyan]Tag Categories:[/bold cyan]")
            for i, category in enumerate(categories):
                if i == selected_category_index:
                    self.console.print(f"  [bold green]▶ {category}[/bold green]")
                else:
                    self.console.print(f"    {category}")
            
            key = self.get_key_press()
            
            if key.lower() == 'q':
                break
            elif key.lower() == 'm':
                # Edit metadata (including Rekordbox comment)
                self.edit_metadata_enhanced(file_path)
            elif key.lower() == 'v':
                # Migrate file to different directory
                self.migrate_file(file_path)
                # Update file_path reference if migration was successful
                if self.current_file != file_path:
                    file_path = self.current_file
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
    
    def set_rekordbox_comment(self, file_path: Path, comment: str) -> bool:
        """Set the Rekordbox comment field (COMM tag)"""
        try:
            audio = File(str(file_path))
            
            if audio is None:
                return False
            
            # Ensure tags exist
            if not hasattr(audio, 'tags') or audio.tags is None:
                if file_path.suffix.lower() == '.mp3':
                    audio.tags = ID3()
                else:
                    audio.add_tags()
            
            # Import COMM for creating the comment tag
            from mutagen.id3 import COMM
            
            # Create the Rekordbox comment tag
            comm_tag = COMM(encoding=3, lang="eng", desc="", text=comment)
            
            # Remove any existing COMM tags with the same parameters
            if hasattr(audio.tags, 'getall'):
                existing_comms = audio.tags.getall("COMM")
                for existing_comm in existing_comms:
                    if hasattr(existing_comm, 'lang') and hasattr(existing_comm, 'desc'):
                        if existing_comm.lang == "eng" and existing_comm.desc == "":
                            audio.tags.delall("COMM")
                            break
            
            # Add the new comment tag
            if hasattr(audio.tags, 'add'):
                audio.tags.add(comm_tag)
            else:
                # For formats that don't support add method
                audio.tags["COMM"] = comm_tag
            
            # Save the file
            audio.save()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set Rekordbox comment on {file_path}: {e}")
            return False
    
    def get_rekordbox_comment(self, file_path: Path) -> Optional[str]:
        """Get the Rekordbox comment field (COMM tag)"""
        try:
            audio = File(str(file_path))
            
            if audio is None or not hasattr(audio, 'tags') or audio.tags is None:
                return None
            
            if hasattr(audio.tags, 'getall'):
                for comm in audio.tags.getall("COMM"):
                    if hasattr(comm, 'lang') and hasattr(comm, 'desc') and hasattr(comm, 'text'):
                        if comm.lang == "eng" and comm.desc == "":
                            return str(comm.text[0])
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not read Rekordbox comment from {file_path}: {e}")
            return None
    
    def edit_rekordbox_comment(self, file_path: Path) -> None:
        """Edit the Rekordbox comment field"""
        current_comment = self.get_rekordbox_comment(file_path) or ""
        
        self.console.print(f"\n[bold yellow]Rekordbox Comment[/bold yellow]")
        self.console.print("This comment will be visible in Rekordbox")
        
        if current_comment:
            self.console.print(f"Current comment: {current_comment}")
        
        new_comment = Prompt.ask("Enter new comment (or press Enter to clear)", default="")
        
        if new_comment != current_comment:
            if self.set_rekordbox_comment(file_path, new_comment):
                if new_comment:
                    self.console.print(f"[green]Comment updated: {new_comment}[/green]")
                else:
                    self.console.print("[green]Comment cleared[/green]")
            else:
                self.console.print("[red]Failed to update comment[/red]")
        
        # Brief pause to show the message
        import time
        time.sleep(1)
    
    def get_metadata_fields(self) -> List[str]:
        """Get the list of metadata fields we can edit"""
        return ['title', 'artist', 'album', 'date', 'genre', 'bpm', 'key', 'rekordbox_comment']
    
    def display_metadata_fields(self, fields: List[str], selected_index: int) -> None:
        """Display metadata fields with arrow key navigation"""
        self.console.print("\n[bold cyan]Metadata Fields:[/bold cyan]")
        self.console.print("Use ↑/↓ to navigate, Enter/→ to edit, q to quit")
        
        for i, field in enumerate(fields):
            if i == selected_index:
                if field == 'rekordbox_comment':
                    self.console.print(f"  [bold green]▶ [yellow]Rekordbox Comment[/yellow][/bold green]")
                else:
                    self.console.print(f"  [bold green]▶ {field.title()}[/bold green]")
            else:
                if field == 'rekordbox_comment':
                    self.console.print(f"    [yellow]Rekordbox Comment[/yellow]")
                else:
                    self.console.print(f"    {field.title()}")
    
    def set_metadata_field(self, file_path: Path, field: str, value: str) -> bool:
        """Set a metadata field in a music file"""
        try:
            audio = File(str(file_path))
            
            if audio is None:
                return False
            
            # Ensure tags exist
            if not hasattr(audio, 'tags') or audio.tags is None:
                if file_path.suffix.lower() == '.mp3':
                    audio.tags = ID3()
                else:
                    audio.add_tags()
            
            # Map field names to tag keys
            field_mappings = {
                'title': 'TIT2',
                'artist': 'TPE1', 
                'album': 'TALB',
                'date': 'TDRC',
                'genre': 'TCON',
                'bpm': 'TBPM',
                'key': 'TKEY'
            }
            
            tag_key = field_mappings.get(field)
            if not tag_key:
                return False
            
            # Import the appropriate tag class
            from mutagen.id3 import TIT2, TPE1, TALB, TDRC, TCON, TBPM, TKEY
            
            tag_classes = {
                'TIT2': TIT2,
                'TPE1': TPE1,
                'TALB': TALB,
                'TDRC': TDRC,
                'TCON': TCON,
                'TBPM': TBPM,
                'TKEY': TKEY
            }
            
            tag_class = tag_classes.get(tag_key)
            if not tag_class:
                return False
            
            # Create the tag
            tag = tag_class(encoding=3, text=value)
            
            # Add or update the tag
            if hasattr(audio.tags, 'add'):
                # Remove existing tag first
                if hasattr(audio.tags, 'delall'):
                    audio.tags.delall(tag_key)
                audio.tags.add(tag)
            else:
                # For formats that don't support add method
                audio.tags[tag_key] = tag
            
            # Save the file
            audio.save()
            return True
            
        except Exception as e:
            logger.error(f"Failed to set metadata field {field} on {file_path}: {e}")
            return False
    
    def edit_metadata_field(self, file_path: Path, field: str) -> None:
        """Edit a specific metadata field"""
        if field == 'rekordbox_comment':
            # Handle Rekordbox comment editing
            current_comment = self.get_rekordbox_comment(file_path) or ""
            
            self.console.print(f"\n[bold yellow]Edit Rekordbox Comment[/bold yellow]")
            self.console.print("This comment will be visible in Rekordbox")
            
            if current_comment:
                self.console.print(f"Current comment: {current_comment}")
            
            new_comment = Prompt.ask("Enter new comment (or press Enter to clear)", default="")
            
            if new_comment != current_comment:
                if self.set_rekordbox_comment(file_path, new_comment):
                    if new_comment:
                        self.console.print(f"[green]Comment updated: {new_comment}[/green]")
                    else:
                        self.console.print("[green]Comment cleared[/green]")
                else:
                    self.console.print("[red]Failed to update comment[/red]")
        else:
            # Handle regular metadata fields
            current_metadata = self.get_audio_metadata(file_path)
            current_value = current_metadata.get(field, "")
            
            self.console.print(f"\n[bold green]Edit {field.title()}[/bold green]")
            
            if current_value:
                self.console.print(f"Current value: {current_value}")
            
            new_value = Prompt.ask(f"Enter new {field} (or press Enter to clear)", default="")
            
            if new_value != current_value:
                if self.set_metadata_field(file_path, field, new_value):
                    if new_value:
                        self.console.print(f"[green]{field.title()} updated: {new_value}[/green]")
                    else:
                        self.console.print(f"[green]{field.title()} cleared[/green]")
                else:
                    self.console.print(f"[red]Failed to update {field}[/red]")
        
        # Brief pause to show the message
        import time
        time.sleep(1)
    
    def edit_metadata_enhanced(self, file_path: Path) -> None:
        """Enhanced interactive metadata editing with arrow key navigation"""
        fields = self.get_metadata_fields()
        if not fields:
            self.console.print("[red]No metadata fields available![/red]")
            return
        
        selected_field_index = 0
        
        while True:
            self.console.clear()
            self.display_file_info(file_path)
            self.display_metadata_fields(fields, selected_field_index)
            
            key = self.get_key_press()
            
            if key.lower() == 'q':
                break
            elif key == 'up':
                selected_field_index = max(0, selected_field_index - 1)
            elif key == 'down':
                selected_field_index = min(len(fields) - 1, selected_field_index + 1)
            elif key in ['enter', 'right']:
                # Edit the selected field
                selected_field = fields[selected_field_index]
                self.edit_metadata_field(file_path, selected_field)
    
    def migrate_file(self, file_path: Path) -> None:
        """Migrate a file to a chosen directory after tagging"""
        self.console.print(f"\n[bold cyan]File Migration[/bold cyan]")
        self.console.print(f"Current file: {file_path.name}")
        self.console.print(f"Current location: {file_path.parent}")
        
        # Get destination path from user with tab completion
        self.console.print("\n[bold yellow]Enter destination directory:[/bold yellow]")
        self.console.print("(Use Tab for autocomplete, or type a relative/absolute path)")
        
        # Use readline for tab completion if available
        try:
            import readline
            import glob
            
            def complete_path(text, state):
                """Tab completion function for file paths"""
                if not text:
                    completions = ['.', '..', '~'] + [str(p.name) + '/' for p in Path('.').iterdir() if p.is_dir()]
                else:
                    # Handle tilde expansion
                    if text.startswith('~'):
                        text = str(Path.home()) + text[1:]
                    
                    # Find matching paths
                    path = Path(text)
                    if path.exists() and path.is_dir():
                        # If it's a complete directory, show its contents
                        completions = [str(path / p.name) + ('/' if p.is_dir() else '') for p in path.iterdir()]
                    else:
                        # Find partial matches
                        parent = path.parent
                        if not parent.exists():
                            parent = Path('.')
                        
                        pattern = path.name + '*'
                        completions = []
                        for p in parent.glob(pattern):
                            if p.is_dir():
                                completions.append(str(p) + '/')
                            else:
                                completions.append(str(p))
                
                # Filter and return completions
                filtered = [c for c in completions if c.startswith(text)]
                return filtered[state] if state < len(filtered) else None
            
            readline.set_completer(complete_path)
            readline.parse_and_bind('tab: complete')
            
        except ImportError:
            self.console.print("[yellow]Tab completion not available on this system[/yellow]")
        
        # Get user input for destination
        destination_input = input("Destination: ").strip()
        
        if not destination_input:
            self.console.print("[yellow]Migration cancelled.[/yellow]")
            return
        
        # Handle tilde expansion
        if destination_input.startswith('~'):
            destination_input = str(Path.home()) + destination_input[1:]
        
        # Convert to Path object
        try:
            destination_path = Path(destination_input).resolve()
        except Exception as e:
            self.console.print(f"[red]Invalid path: {e}[/red]")
            return
        
        # Check if destination exists and is a directory
        if not destination_path.exists():
            # Ask if user wants to create the directory
            self.console.print(f"\n[bold yellow]Directory '{destination_path}' does not exist.[/bold yellow]")
            create_dir = input("Create it? (y/n): ").strip().lower()
            
            if create_dir in ['y', 'yes']:
                try:
                    destination_path.mkdir(parents=True, exist_ok=True)
                    self.console.print(f"[green]Created directory: {destination_path}[/green]")
                except Exception as e:
                    self.console.print(f"[red]Failed to create directory: {e}[/red]")
                    return
            else:
                self.console.print("[yellow]Migration cancelled.[/yellow]")
                return
        elif not destination_path.is_dir():
            self.console.print(f"[red]'{destination_path}' is not a directory![/red]")
            return
        
        # Calculate the new file path
        new_file_path = destination_path / file_path.name
        
        # Check if file already exists at destination
        if new_file_path.exists():
            self.console.print(f"\n[bold red]Warning: File already exists at destination![/bold red]")
            self.console.print(f"Destination: {new_file_path}")
            
            overwrite = input("Overwrite existing file? (y/n): ").strip().lower()
            if overwrite not in ['y', 'yes']:
                self.console.print("[yellow]Migration cancelled.[/yellow]")
                return
        
        # Show migration summary and confirm
        self.console.print(f"\n[bold cyan]Migration Summary:[/bold cyan]")
        self.console.print(f"From: {file_path}")
        self.console.print(f"To:   {new_file_path}")
        
        confirm = input("\nAre you sure you want to move this file? (y/n): ").strip().lower()
        
        if confirm not in ['y', 'yes']:
            self.console.print("[yellow]Migration cancelled.[/yellow]")
            return
        
        # Perform the migration
        try:
            import shutil
            shutil.move(str(file_path), str(new_file_path))
            self.console.print(f"[green]Successfully migrated file to: {new_file_path}[/green]")
            
            # Update the current file path reference if this is the current file being tagged
            if self.current_file == file_path:
                self.current_file = new_file_path
                
        except Exception as e:
            self.console.print(f"[red]Failed to migrate file: {e}[/red]")
            logger.error(f"Failed to migrate {file_path} to {new_file_path}: {e}")