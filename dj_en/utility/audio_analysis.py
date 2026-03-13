"""Audio analysis utilities for quality scoring and metadata extraction."""

import json
import subprocess
from pathlib import Path
from typing import Optional
from dj_en.logging import get_logger

logger = get_logger(__name__)


def get_audio_metadata(file_path: Path) -> Optional[dict]:
    """
    Get audio metadata using ffprobe.

    Extracts technical audio information including codec, bitrate, and sample rate
    from audio files using FFmpeg's ffprobe utility.

    Args:
        file_path: Path to the audio file

    Returns:
        dict: Audio stream metadata if successful, None otherwise
              Contains keys like 'codec_name', 'bit_rate', 'sample_rate'
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            str(file_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            logger.warning(f"ffprobe failed for {file_path}: {result.stderr}")
            return None

        data = json.loads(result.stdout)

        # Find the first audio stream
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                return stream

        return None

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to get metadata for {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting metadata for {file_path}: {e}")
        return None


def analyze_audio_quality(file_path: Path) -> float:
    """
    Analyze audio file and return quality score between 0.0 and 1.0.

    The quality score is calculated based on three factors:
    - Bitrate (40% weight): Higher bitrates indicate better quality
    - Sample rate (30% weight): Higher sample rates preserve more audio detail
    - File format (30% weight): Lossless formats score higher than lossy

    Quality scoring breakdown:
    - 0.85-1.0: High quality (lossless or 320kbps+)
    - 0.6-0.84: Medium quality (192-256kbps)
    - 0.0-0.59: Low quality (<192kbps or low sample rate)

    Args:
        file_path: Path to the audio file to analyze

    Returns:
        float: Quality score between 0.0 (lowest) and 1.0 (highest)
               Returns 0.3 as default for unreadable files or analysis failures
    """
    try:
        # Get audio metadata using ffprobe
        metadata = get_audio_metadata(file_path)
        if not metadata:
            return 0.3  # Default low score for unreadable files

        # Extract key metrics
        bitrate = metadata.get('bit_rate', 0)
        sample_rate = metadata.get('sample_rate', 0)
        codec_name = metadata.get('codec_name', '').lower()

        # Convert to numeric values
        try:
            bitrate = int(bitrate) if bitrate else 0
            sample_rate = int(sample_rate) if sample_rate else 0
        except (ValueError, TypeError):
            bitrate = 0
            sample_rate = 0

        # Calculate quality score
        quality_score = 0.0

        # Bitrate scoring (40% of total score)
        if codec_name in ['flac', 'alac', 'pcm_s16le', 'pcm_s24le']:
            # Lossless formats get high bitrate score
            quality_score += 0.4
        elif bitrate >= 320000:  # 320kbps+
            quality_score += 0.4
        elif bitrate >= 256000:  # 256kbps
            quality_score += 0.32
        elif bitrate >= 192000:  # 192kbps
            quality_score += 0.24
        elif bitrate >= 128000:  # 128kbps
            quality_score += 0.16
        else:
            quality_score += 0.08

        # Sample rate scoring (30% of total score)
        if sample_rate >= 96000:  # High-res audio
            quality_score += 0.3
        elif sample_rate >= 48000:  # Professional standard
            quality_score += 0.28
        elif sample_rate >= 44100:  # CD quality
            quality_score += 0.25
        elif sample_rate >= 22050:  # Acceptable
            quality_score += 0.15
        else:
            quality_score += 0.05

        # File format bonus (30% of total score)
        if codec_name in ['flac', 'alac']:  # Lossless
            quality_score += 0.3
        elif codec_name in ['pcm_s16le', 'pcm_s24le']:  # Uncompressed
            quality_score += 0.28
        elif codec_name == 'mp3' and bitrate >= 320000:  # High quality MP3
            quality_score += 0.22
        elif codec_name == 'mp3' and bitrate >= 256000:  # Good MP3
            quality_score += 0.18
        elif codec_name == 'aac' and bitrate >= 256000:  # High quality AAC
            quality_score += 0.2
        else:
            quality_score += 0.1

        # Ensure score is between 0.0 and 1.0
        quality_score = max(0.0, min(1.0, quality_score))

        logger.debug(f"Quality analysis for {file_path.name}: bitrate={bitrate}, sample_rate={sample_rate}, codec={codec_name}, score={quality_score:.3f}")

        return quality_score

    except Exception as e:
        logger.warning(f"Failed to analyze audio quality for {file_path}: {e}")
        return 0.3  # Default score for analysis failures
