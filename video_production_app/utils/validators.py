"""
Input validation utilities for Video Production App.

This module provides functions to validate user inputs, file paths, and other
data to prevent errors and security issues.
"""

from pathlib import Path
from typing import Tuple, Union, Optional, List
from ..config import SUPPORTED_VIDEO_FORMATS, FILE_LIMITS


def normalize_path(path: Union[str, Path]) -> Path:
    """
    Convert string or Path to Path object, handling Windows paths.
    
    Args:
        path: String or Path object
        
    Returns:
        Path object
    """
    if isinstance(path, str):
        return Path(path)
    return path


def validate_video_path(file_path: Union[str, Path]) -> Tuple[bool, str]:
    """
    Validate video file path.
    
    Checks:
    - File exists
    - Is a file (not directory)
    - Has valid video extension
    - File size is within limits
    
    Args:
        file_path: Path to video file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        path = normalize_path(file_path)
        
        # Check if exists
        if not path.exists():
            return False, "File does not exist"
        
        # Check if file (not directory)
        if not path.is_file():
            return False, "Path is not a file"
        
        # Check file extension
        if path.suffix.lower() not in SUPPORTED_VIDEO_FORMATS:
            return False, f"Invalid file type: {path.suffix}. Supported: {', '.join(SUPPORTED_VIDEO_FORMATS)}"
        
        # Check file size (only if limit is set)
        if FILE_LIMITS["max_file_size_mb"] is not None:
            max_size_bytes = FILE_LIMITS["max_file_size_mb"] * 1024 * 1024
            file_size = path.stat().st_size
            
            if file_size > max_size_bytes:
                file_size_mb = file_size / (1024 * 1024)
                max_size_mb = FILE_LIMITS["max_file_size_mb"]
                return False, f"File too large ({file_size_mb:.1f}MB). Maximum: {max_size_mb}MB"
        
        # Check if file is readable
        if not path.is_file() or not path.stat().st_size > 0:
            return False, "File is empty or not readable"
        
        return True, ""
        
    except PermissionError:
        return False, "Permission denied: Cannot access file"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def validate_track_index(track_index: Union[int, str], max_tracks: int, 
                        available_indices: Optional[List[int]] = None) -> Tuple[bool, str]:
    """
    Validate audio track index.
    
    Args:
        track_index: Track index to validate
        max_tracks: Maximum number of tracks (for backward compatibility)
        available_indices: Optional list of actual track indices (FFprobe stream indices)
                         If provided, validates against these instead of 0-based range
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        index = int(track_index)
        
        # If available_indices is provided, check against actual stream indices
        if available_indices is not None and len(available_indices) > 0:
            if index not in available_indices:
                return False, f"Track index {index} is not available. Available tracks: {', '.join(map(str, available_indices))}."
            return True, ""
        
        # Otherwise, use 0-based validation (backward compatibility)
        if index < 0:
            return False, "Track index must be >= 0"
        if index >= max_tracks:
            return False, f"Track index {index} is out of range (max: {max_tracks - 1})"
        return True, ""
    except (ValueError, TypeError):
        return False, f"Invalid track index: {track_index}"


def validate_trim_values(trim_start: Union[float, str], trim_end: Union[float, str, None], 
                        duration: float) -> Tuple[bool, str]:
    """
    Validate trim start and end values.
    
    Args:
        trim_start: Start time in seconds
        trim_end: End time in seconds (None for full duration)
        duration: Total video duration in seconds
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        start = float(trim_start) if trim_start else 0.0
        
        if start < 0:
            return False, "Trim start must be >= 0"
        
        if start >= duration:
            return False, f"Trim start ({start:.2f}s) must be < video duration ({duration:.2f}s)"
        
        if trim_end is not None:
            end = float(trim_end)
            
            if end <= start:
                return False, f"Trim end ({end:.2f}s) must be > trim start ({start:.2f}s)"
            
            if end > duration:
                return False, f"Trim end ({end:.2f}s) must be <= video duration ({duration:.2f}s)"
        
        return True, ""
        
    except (ValueError, TypeError) as e:
        return False, f"Invalid trim value: {str(e)}"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators and dangerous characters
    dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    return sanitized if sanitized else "untitled"

