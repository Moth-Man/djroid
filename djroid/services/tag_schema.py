import json
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.text import Text
from rich import box
import click

class TagSchema:
    def __init__(self):
        self.console = Console()
        self.schema_file = Path.home() / '.djroid' / 'tag_schema.json'
        self.schema: Dict[str, List[str]] = {}
        
    def load_schema(self) -> Dict[str, List[str]]:
        """Load existing schema from file"""
        if self.schema_file.exists():
            with open(self.schema_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_schema(self, schema: Dict[str, List[str]]):
        """Save schema to file"""
        self.schema_file.parent.mkdir(exist_ok=True)
        with open(self.schema_file, 'w') as f:
            json.dump(schema, f, indent=2)
    
    def display_schema_table(self, schema: Dict[str, List[str]], title: str = "Current Tag Schema"):
        """Display schema as a beautiful table"""
        table = Table(title=title, box=box.ROUNDED, show_lines=True)
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Type", style="blue", no_wrap=True)
        table.add_column("Values/Config", style="green")
        table.add_column("Count", style="yellow", justify="center")
        
        for category, config in schema.items():
            if isinstance(config, dict) and config.get("type") == "rating":
                # Rating category
                max_rating = config.get("max_rating", "unknown")
                values_str = f"1-{max_rating} (rating scale)"
                count = max_rating
                table.add_row(category, "rating", values_str, str(count))
            elif isinstance(config, list):
                # Regular category
                values_str = ", ".join(config) if config else "(empty)"
                count = len(config)
                table.add_row(category, "multi-value", values_str, str(count))
            else:
                # Unknown format
                values_str = str(config)
                count = "?"
                table.add_row(category, "unknown", values_str, str(count))
        
        self.console.print(table)
    
    def get_default_schema(self) -> Dict[str, List[str]]:
        """Get default schema with common DJ categories"""
        return {
            "function": ["intro", "build", "drop", "breakdown", "outro", "transition"],
            "utility": ["warmup", "peak time", "closing", "backup"],
            "setting": ["club", "festival", "warehouse", "outdoor", "intimate"],
            "situation": ["crowd control", "energy boost", "chill out", "dance floor"],
            "demographic": ["underground", "mainstream", "experimental", "commercial"]
        }
    
    def add_category(self, schema: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Add a new category to the schema"""
        self.console.print("\n[bold cyan]Adding New Category[/bold cyan]")
        
        while True:
            category_name = Prompt.ask("Enter category name").strip()
            if not category_name:
                self.console.print("[red]Category name cannot be empty![/red]")
                continue
            
            if category_name in schema:
                self.console.print(f"[red]Category '{category_name}' already exists![/red]")
                continue
            
            break
        
        # Add values to the category
        values = self.add_values_to_category(category_name, [])
        schema[category_name] = values
        
        return schema
    
    def add_values_to_category(self, category_name: str, existing_values: List[str]) -> List[str]:
        """Add values to a category interactively"""
        values = existing_values.copy()
        
        self.console.print(f"\n[bold green]Adding values to '{category_name}' category[/bold green]")
        self.console.print("Enter values one by one. Press Enter with empty input to finish.")
        
        while True:
            value = Prompt.ask(f"Add value to '{category_name}'").strip()
            if not value:
                break
            
            if value in values:
                self.console.print(f"[yellow]Value '{value}' already exists in this category![/yellow]")
                continue
            
            values.append(value)
            self.console.print(f"[green]Added: {value}[/green]")
        
        return values
    
    def modify_category(self, schema: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Modify an existing category"""
        if not schema:
            self.console.print("[red]No categories to modify![/red]")
            return schema
        
        # Show categories for selection
        categories = list(schema.keys())
        self.console.print("\n[bold cyan]Select category to modify:[/bold cyan]")
        for i, category in enumerate(categories, 1):
            self.console.print(f"{i}. {category}")
        
        while True:
            try:
                choice = IntPrompt.ask("Enter category number", default=1)
                if 1 <= choice <= len(categories):
                    category_name = categories[choice - 1]
                    break
                else:
                    self.console.print("[red]Invalid choice![/red]")
            except ValueError:
                self.console.print("[red]Please enter a valid number![/red]")
        
        # Show current values
        current_values = schema[category_name]
        self.console.print(f"\n[bold]Current values for '{category_name}':[/bold]")
        if current_values:
            for value in current_values:
                self.console.print(f"  • {value}")
        else:
            self.console.print("  (no values)")
        
        # Ask what to do
        action = Prompt.ask(
            "Choose action",
            choices=["add", "remove", "replace", "cancel"],
            default="add"
        )
        
        if action == "cancel":
            return schema
        elif action == "add":
            new_values = self.add_values_to_category(category_name, current_values)
            schema[category_name] = new_values
        elif action == "remove":
            if not current_values:
                self.console.print("[yellow]No values to remove![/yellow]")
                return schema
            
            self.console.print("\n[bold]Select values to remove:[/bold]")
            for i, value in enumerate(current_values, 1):
                self.console.print(f"{i}. {value}")
            
            while True:
                try:
                    choice = IntPrompt.ask("Enter value number to remove. Hit enter to cancel.", default=0)
                    if choice == 0:
                        return schema
                    if 1 <= choice <= len(current_values):
                        removed_value = current_values.pop(choice - 1)
                        self.console.print(f"[green]Removed: {removed_value}[/green]")
                        break
                    else:
                        self.console.print("[red]Invalid choice![/red]")
                except ValueError:
                    self.console.print("[red]Please enter a valid number![/red]")
            
            schema[category_name] = current_values
        elif action == "replace":
            new_values = self.add_values_to_category(category_name, [])
            schema[category_name] = new_values
        
        return schema
    
    def remove_category(self, schema: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Remove a category from the schema"""
        if not schema:
            self.console.print("[red]No categories to remove![/red]")
            return schema
        
        # Show categories for selection
        categories = list(schema.keys())
        self.console.print("\n[bold red]Select category to remove:[/bold red]")
        for i, category in enumerate(categories, 1):
            self.console.print(f"{i}. {category}")
        
        while True:
            try:
                choice = IntPrompt.ask("Enter category number", default=1)
                if 1 <= choice <= len(categories):
                    category_name = categories[choice - 1]
                    break
                else:
                    self.console.print("[red]Invalid choice![/red]")
            except ValueError:
                self.console.print("[red]Please enter a valid number![/red]")
        
        # Confirm removal
        if Confirm.ask(f"Are you sure you want to remove category '{category_name}'?"):
            del schema[category_name]
            self.console.print(f"[green]Removed category: {category_name}[/green]")
        
        return schema

    def add_rating_category(self, schema: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Add a rating category with max_rating"""
        self.console.print("\n[bold cyan]Adding Rating Category[/bold cyan]")
        
        while True:
            category_name = Prompt.ask("Enter rating category name (e.g., 'energy', 'vibe')").strip()
            if not category_name:
                self.console.print("[red]Category name cannot be empty![/red]")
                continue
            
            if category_name in schema:
                self.console.print(f"[red]Category '{category_name}' already exists![/red]")
                continue
            
            break
        
        # Get the max rating
        while True:
            try:
                max_rating = IntPrompt.ask("Enter maximum rating value (minimum is 1)", default=5)
                
                if max_rating < 1:
                    self.console.print("[red]Maximum rating must be at least 1![/red]")
                    continue
                
                if max_rating > 20:
                    self.console.print("[yellow]Warning: Large rating range may be unwieldy[/yellow]")
                    if not Confirm.ask("Continue anyway?"):
                        continue
                
                break
            except ValueError:
                self.console.print("[red]Please enter a valid number![/red]")
        
        # Create rating category with the specified JSON structure
        schema[category_name] = {
            "type": "rating",
            "max_rating": max_rating
        }
        
        self.console.print(f"[green]Added rating category '{category_name}' with max rating {max_rating}[/green]")
        
        return schema

    def get_display_content(self) -> str:
        """Get formatted content for GUI display"""
        schema = self.load_schema()
        
        if not schema:
            return "No tag schema found. Run 'djroid tag-schema' to create one."
        
        content_lines = []
        for category, values in schema.items():
            if isinstance(values, list):
                content_lines.append(f"{category.upper()}")
                for value in values[:10]:  # Show first 10 values
                    content_lines.append(f"• {value}")
                if len(values) > 10:
                    content_lines.append(f"• ... ({len(values) - 10} more)")
                content_lines.append("")  # Empty line between categories
            elif isinstance(values, dict) and values.get("type") == "rating":
                max_rating = values.get("max_rating", 5)
                content_lines.append(f"{category.upper()} (Rating 1-{max_rating})")
                content_lines.append("")
        
        return "\n".join(content_lines)

    def setup_schema(self):
        """Main method to setup the tag schema interactively"""
        self.console.print(Panel.fit(
            "[bold blue]DJroid Tag Schema Setup[/bold blue]\n"
            "Create categories and values for tagging your music library",
            border_style="blue"
        ))
        
        # Load existing schema or start fresh
        self.schema = self.load_schema()
        
        if self.schema:
            self.console.print("[green]Found existing schema![/green]")
            self.display_schema_table(self.schema, "Existing Schema")
            
            if not Confirm.ask("Do you want to modify the existing schema?", default=False):
                self.console.print("[yellow]Using existing schema.[/yellow]")
                return
        else:
            # Offer default schema
            self.console.print("\n[bold]No existing schema found.[/bold]")
            if Confirm.ask("Would you like to use the default categories?", default=True):
                self.schema = self.get_default_schema()
                self.display_schema_table(self.schema, "Default Schema")
        
        # Main interaction loop
        while True:
            self.console.print("\n" + "="*50)
            self.display_schema_table(self.schema, "Current Schema")
            
            action = Prompt.ask(
                "\nChoose an action",
                choices=["add", "add_rating", "modify", "remove", "finish"],
                default="finish"
            )
            
            if action == "finish":
                break
            elif action == "add":
                self.schema = self.add_category(self.schema)
            elif action == "add_rating":
                self.schema = self.add_rating_category(self.schema)
            elif action == "modify":
                self.schema = self.modify_category(self.schema)
            elif action == "remove":
                self.schema = self.remove_category(self.schema)
        
        # Save schema
        self.save_schema(self.schema)
        self.console.print(f"\n[bold green]Schema saved to: {self.schema_file}[/bold green]")
        self.console.print("[green]You can now use the 'tag' command to tag your music files![/green]")
