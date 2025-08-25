#!/bin/bash
# Activate virtual environment and run the textual interface

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Starting Djroid HAL 9000 Interface..."
echo "Use arrow keys to navigate, Enter to select, \` to toggle HAL, Q to quit"
echo "-" * 60

python test_textual.py