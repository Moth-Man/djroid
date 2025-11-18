"""Waveform preview component for displaying song waveforms with gradient styling."""

from typing import List


# Gradient pattern class names that correspond to CSS styles in styles.tcss
WAVEFORM_GRADIENT_PATTERNS = [
    "gradient-1",
    "gradient-2",
    "gradient-3",
    "gradient-4",
    "gradient-5",
    "gradient-6",
    "gradient-7",
    "gradient-8",
    "gradient-9",
    "gradient-10",
]


def get_waveform_gradient_class(index: int) -> str:
    """
    Get the gradient CSS class for a waveform at the given index.

    The gradient patterns cycle through a set of predefined color schemes
    to provide visual variety in the waveform display.

    Args:
        index: The index of the song/waveform (0-based)

    Returns:
        str: The CSS class name for the gradient pattern

    Example:
        >>> get_waveform_gradient_class(0)
        'gradient-1'
        >>> get_waveform_gradient_class(10)
        'gradient-1'  # Cycles back to the first pattern
    """
    return WAVEFORM_GRADIENT_PATTERNS[index % len(WAVEFORM_GRADIENT_PATTERNS)]
