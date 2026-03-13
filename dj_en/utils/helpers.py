import os
from pathlib import Path
from typing import List

def get_audio_files(directory: str, recursive: bool = True) -> List[Path]:
    """Get all audio files in a directory."""
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    audio_extensions = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac'}
    files = []
    
    for file_path in directory.rglob('*') if recursive else directory.glob('*'):
        if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
            files.append(file_path)
    
    return files

def format_duration(seconds: float) -> str:
    """Format duration in seconds to MM:SS format."""
    if seconds is None:
        return "00:00"
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}" 