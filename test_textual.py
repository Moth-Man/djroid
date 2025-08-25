#!/usr/bin/env python3
"""
Test script for the Djroid textual interface.
Run this to see the HAL 9000 interface in action.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from djroid.textual.main import main

if __name__ == "__main__":
    print("Starting Djroid HAL 9000 Interface...")
    print("Use arrow keys to navigate, Enter to select, ` to toggle HAL, Q to quit")
    print("-" * 60)
    main()