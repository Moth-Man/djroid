"""
HAL 9000 animated component for the Djroid interface.
Displays pixel art PNG with saturation fluctuation for LED blinking effect.
"""

import os
import math
from PIL import Image, ImageEnhance
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from rich.style import Style

from ..config import HAL_COLORS


class HALComponent(Widget):
    """Animated pixel art component with saturation fluctuation effect."""
    
    # Reactive attributes
    visible = reactive(True)
    saturation_level = reactive(1.0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.animation_timer = None
        self.animation_step = 0
        self.pixel_art_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "assets", 
            "pixel_art_large.png"
        )
        self.original_image = None
        self._load_image()
    
    def _load_image(self) -> None:
        """Load the pixel art PNG image."""
        try:
            if os.path.exists(self.pixel_art_path):
                self.original_image = Image.open(self.pixel_art_path)
                # Keep square resolution, use overflow clipping to fit in component
                self.original_image = self.original_image.resize((35, 35), Image.Resampling.NEAREST)
            else:
                self.original_image = None
        except Exception as e:
            self.original_image = None
        
    def compose(self) -> ComposeResult:
        """Compose the HAL component with the pixel art display."""
        yield Static(
            "",
            id="hal_display",
            classes="hal-frame"
        )
        
    def on_mount(self) -> None:
        """Start the animation when the component mounts."""
        self.start_animation()
        self.update_display()
        
    def start_animation(self) -> None:
        """Start the saturation fluctuation animation."""
        if self.animation_timer:
            self.animation_timer.stop()
        
        self.animation_timer = self.set_interval(
            0.1,  # 10 FPS for smooth animation
            self.animate_saturation
        )
        
    def stop_animation(self) -> None:
        """Stop the saturation animation."""
        if self.animation_timer:
            self.animation_timer.stop()
            self.animation_timer = None
            
    def animate_saturation(self) -> None:
        """Update saturation level for LED blinking effect."""
        self.animation_step += 1
        # Create a sine wave for smooth saturation fluctuation
        # Range from 0.3 to 1.0 saturation
        self.saturation_level = 0.65 + 0.35 * math.sin(self.animation_step * 0.15)
        self.update_display()
        
    def update_display(self) -> None:
        """Update the displayed pixel art with current saturation."""
        if not self.visible:
            hal_display = self.query_one("#hal_display", Static)
            hal_display.update("")
            return
            
        hal_display = self.query_one("#hal_display", Static)
        
        if self.original_image is None:
            hal_display.update("Image not found")
            return
        
        # Apply saturation and get the modified image
        saturated_image = self._create_saturated_image()
        
        # Update the static widget with the image
        hal_display.update(saturated_image)
    
    def _create_saturated_image(self):
        """Create a saturated version of the image and return it as colored blocks."""
        if self.original_image is None:
            return Text("No image found", style="red")
        
        try:
            # Apply saturation to get the modified image
            img_copy = self.original_image.copy()
            enhancer = ImageEnhance.Color(img_copy)
            saturated_img = enhancer.enhance(self.saturation_level)
            
            # Convert to colored block representation
            return self._image_to_colored_blocks(saturated_img)
            
        except Exception as e:
            return Text(f"Error: {str(e)}", style="red")
    
    def _image_to_colored_blocks(self, image):
        """Convert PIL image to colored Unicode blocks, cropping to fit component properly."""
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        width, height = image.size
        text = Text()
        
        # Use single character for each pixel
        block_char = "█"  # Single block character
        
        # Show maximum vertical pixels to capture the full circle
        max_display_height = 26  # Increased even more to show more vertically
        
        # Crop aggressively from horizontal sides 
        max_display_width = 14   # Reduced significantly from 20 to 15 to crop sides much more
        
        # Calculate which rows and columns to show (center crop both dimensions)
        start_y = max(0, (height - max_display_height) // 2)
        end_y = min(height, start_y + max_display_height)
        
        start_x = max(0, (width - max_display_width) // 2)
        end_x = min(width, start_x + max_display_width)
        
        # Add minimal top padding
        text.append("\n")
        
        for y in range(start_y, end_y):
            # Add horizontal padding for centering
            text.append("  ")  # Left padding
            
            for x in range(start_x, end_x):
                r, g, b = image.getpixel((x, y))
                
                # Create RGB color string for Rich
                color = f"rgb({r},{g},{b})"
                
                # Add colored block
                text.append(block_char, style=Style(color=color))
            
            # Add newline at end of each row
            text.append("\n")
        
        return text
    
        
    def toggle_visibility(self) -> None:
        """Toggle the visibility of the pixel art component."""
        self.visible = not self.visible
        
        hal_display = self.query_one("#hal_display", Static)
        if self.visible:
            self.start_animation()
            self.update_display()
        else:
            self.stop_animation()
            hal_display.update("")
            
    def watch_visible(self, visible: bool) -> None:
        """React to visibility changes."""
        if visible:
            self.update_display()
        else:
            hal_display = self.query_one("#hal_display", Static)
            hal_display.update("")