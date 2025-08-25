"""
Configuration settings for the Djroid Textual UI.
Defines colors, themes, and interface settings.
"""

# Color palette - red to green progression
COLORS = {
    "background": "#282828",          # Dark gray background
    "chat_box": "#1d2021",           # Darker gray for chat box
    "primary": "#cc241d",            # Red
    "secondary": "#d65d0e",          # Orange  
    "accent": "#d79921",             # Yellow
    "success": "#98971a",            # Green
    "text": "#ebdbb2",               # Light text
    "muted": "#928374",              # Muted text
    "highlight": "#fabd2f",          # Bright yellow for highlights
    "border": "#504945",             # Border color
}

# Command colors (red -> orange -> yellow -> green progression)
COMMAND_COLORS = {
    "djtag": "red",
    "djschema": "#d65d0e",  # Orange
    "djscan": "yellow", 
    "djcrate": "green"
}

# ASCII art colors
HAL_COLORS = {
    "frame": "cyan",
    "eye_normal": "red",
    "eye_dim": "dark_red",
    "eye_bright": "bright_red",
    "text": "white",
    "border": "blue"
}

# Layout dimensions
LAYOUT = {
    "hal_width_ratio": 0.2,          # HAL takes 1/5 of width
    "chat_width_ratio": 0.8,         # Chat takes 4/5 of width
    "min_terminal_width": 80,        # Minimum terminal width
    "min_terminal_height": 24,       # Minimum terminal height
}

# Animation settings
ANIMATION = {
    "hal_frame_duration": 1.2,       # Seconds between HAL frames
    "command_highlight_speed": 0.3,  # Speed of command highlighting
    "fade_duration": 0.5,            # Fade in/out duration
}

# Key bindings
KEYBINDINGS = {
    "quit": ["q", "escape"],
    "toggle_hal": ["`"],
    "nav_up": ["up", "k"],
    "nav_down": ["down", "j"],
    "nav_left": ["left", "h"],
    "nav_right": ["right", "l"],
    "select": ["enter", "space"],
    "back": ["backspace", "escape"],
}

# Command descriptions for djroid contextual blurbs
COMMAND_DESCRIPTIONS = {
    "djtag": "Interactive music file tagging with your custom schema. Browse songs, edit metadata, and organize your collection with intelligent tag management.",
    "djschema": "Define and manage your tagging categories. Create multi-value tags and rating scales to structure your music organization system.",
    "djscan": "Recursively scan directories to build your music database. Extract metadata, apply tags, and generate collection analytics and insights.",
    "djcrate": "Create and manage custom playlists and collections. Group tracks by energy, genre, mood, or any criteria that matters to your DJ sets."
}