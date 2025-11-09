"""
Silence detection and segment parsing for Video Production App.

This module handles the core functionality of detecting silence in audio tracks
and converting that information into segments that can be used for video processing.
It uses FFmpeg's silencedetect filter to analyze audio and identify quiet periods.

Key functions:
- detect_silence: Run FFmpeg silence detection on an audio track
- parse_segments: Convert silence detection output into usable segments
- Segment validation and padding logic

The silence detection works by analyzing audio levels and identifying periods
where the volume drops below a specified threshold for a minimum duration.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Callable, Optional, List, Tuple, Dict, Any


def detect_silence(video_file: Path, track_index: int, ffmpeg_path: str, settings: Dict[str, Any], 
                  status_callback: Callable[[str], None], trim_start: float = 0, 
                  trim_end: Optional[float] = None) -> str:
    """
    Detect silence in an audio track using FFmpeg's silencedetect filter.
    
    This function runs FFmpeg with the silencedetect filter to analyze an audio
    track and identify periods of silence. The detection is based on volume
    levels and duration thresholds specified in the settings.
    
    Args:
        video_file: Path to the video file containing the audio track
        track_index: Index of the audio track to analyze
        ffmpeg_path: Path to FFmpeg executable (empty string uses system PATH)
        settings: Dictionary containing silence detection parameters:
            - silence_db: Volume threshold in decibels (e.g., -40)
            - silence_duration: Minimum duration for silence in seconds (e.g., 0.7)
        status_callback: Function to call with status messages
        trim_start: Start time for analysis (seconds)
        trim_end: End time for analysis (seconds, None for full duration)
        
    Returns:
        Raw FFmpeg output containing silence detection results
        
    Example:
        settings = {"silence_db": -40, "silence_duration": 0.7}
        output = detect_silence(Path("video.mp4"), 0, "", settings, print)
        # Returns FFmpeg output with silence_start and silence_end markers
    """
    # Tell user what we're doing
    status_callback(f"🤫 Detecting silence in track {track_index}...\n")
    
    # Use provided path or default to system PATH
    ffmpeg_executable = ffmpeg_path or "ffmpeg"
    
    # Get silence detection parameters from settings
    silence_db = settings.get("silence_db", -40)  # Volume threshold in dB
    silence_duration = settings.get("silence_duration", 0.7)  # Minimum duration in seconds
    
    # Build the silence detection filter
    # silencedetect=n=-40dB:d=0.7 means: detect silence below -40dB for at least 0.7 seconds
    silence_filter = f"silencedetect=n={silence_db}dB:d={silence_duration}"
    
    # Start building FFmpeg command
    cmd = [str(ffmpeg_executable), "-hide_banner"]  # Hide FFmpeg banner
    
    # Add trimming if specified
    if trim_start > 0 or trim_end is not None:
        cmd.extend(["-ss", str(trim_start)])  # Start time
        if trim_end is not None:
            cmd.extend(["-to", str(trim_end)])  # End time
    
    # Add input file, track selection, and silence detection
    cmd.extend([
        "-i", str(video_file),  # Input file
        "-map", f"0:{track_index}",  # Select specific audio track
        "-af", silence_filter,  # Apply silence detection filter
        "-f", "null",  # No output file needed
        "-"  # Output to null
    ])
    
    try:
        # Set up Windows-specific startup info to hide console window
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        # Run FFmpeg command
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8', 
            errors='ignore', 
            startupinfo=startupinfo
        )
        
        # Return the stderr output (FFmpeg puts silence detection info there)
        return result.stderr
        
    except Exception as e:
        # If FFmpeg fails, return empty string
        status_callback(f"❌ Error running silence detection: {e}\n")
        return ""


def parse_segments(ffmpeg_output: str, duration: float, settings: Dict[str, Any], 
                  status_callback: Callable[[str], None], trim_start: float = 0) -> List[Dict[str, Any]]:
    """
    Parse FFmpeg silence detection output into all segments (audible and silent).
    
    This function takes the raw output from FFmpeg's silencedetect filter and
    converts it into a chronological list of all segments, both audible and silent.
    It handles edge cases like no silence detected, padding around segments,
    and trimming boundaries.
    
    Args:
        ffmpeg_output: Raw output from FFmpeg's silencedetect filter
        duration: Total duration of the video in seconds
        settings: Dictionary containing padding parameters:
            - pad_before: Padding to add before segments (seconds)
            - pad_after: Padding to add after segments (seconds)
        status_callback: Function to call with status messages
        trim_start: Start time offset for segment calculations
        
    Returns:
        List of dictionaries representing all segments (audible and silent):
        [
            {'start': 0.0, 'end': 1.2, 'type': 'audible', 'keep': True},
            {'start': 1.2, 'end': 1.9, 'type': 'silent', 'keep': False},
            ...
        ]
        
    Example:
        output = "silence_start: 10.5\nsilence_end: 15.2\nsilence_start: 20.0"
        segments = parse_segments(output, 30.0, {"pad_before": 0.1, "pad_after": 0.0}, print)
        # Returns: [
        #     {'start': 0.0, 'end': 10.4, 'type': 'audible', 'keep': True},
        #     {'start': 10.4, 'end': 10.5, 'type': 'silent', 'keep': False},
        #     {'start': 15.2, 'end': 20.0, 'type': 'audible', 'keep': True},
        #     {'start': 20.0, 'end': 20.1, 'type': 'silent', 'keep': False},
        #     {'start': 20.1, 'end': 30.0, 'type': 'audible', 'keep': True}
        # ]
    """
    # Extract silence start and end times from FFmpeg output
    # Look for patterns like "silence_start: 10.5" and "silence_end: 15.2"
    starts = [float(t) + trim_start for t in re.findall(r'silence_start: (\d+\.?\d*)', ffmpeg_output)]
    ends = [float(t) + trim_start for t in re.findall(r'silence_end: (\d+\.?\d*)', ffmpeg_output)]

    # Get padding settings
    pad_before = settings.get("pad_before", 0.1)  # Padding before segments
    pad_after = settings.get("pad_after", 0.0)   # Padding after segments

    # If no silence was detected, treat entire video as one audible segment
    if not starts and not ends:
        status_callback("🤔 No silence detected. Treating entire video as one audible segment.\n")
        return [{
            'start': trim_start,
            'end': duration,
            'type': 'audible',
            'keep': True
        }]

    # Build chronological list of all segments (without padding first)
    all_segments = []
    
    # Handle audible segment before first silence (if any)
    if starts and starts[0] > trim_start:
        # There's audible content from start to first silence
        all_segments.append({
            'start': trim_start,
            'end': starts[0],
            'type': 'audible',
            'keep': True
        })
    
    # Process each silence period and the audible gap after it
    for i in range(len(starts)):
        silence_start = starts[i]
        silence_end = ends[i] if i < len(ends) else duration
        
        # Add the silent segment
        if silence_end > silence_start:
            all_segments.append({
                'start': silence_start,
                'end': silence_end,
                'type': 'silent',
                'keep': False
            })
        
        # Add the audible segment after this silence (gap until next silence or end)
        if i < len(ends):
            # Start of audible segment is end of silence
            audible_start = silence_end
            
            # End of audible segment is start of next silence (or end of video)
            if (i + 1) < len(starts):
                audible_end = starts[i + 1]
            else:
                audible_end = duration
            
            # Only add if there's a gap (positive duration)
            if audible_end > audible_start:
                all_segments.append({
                    'start': audible_start,
                    'end': audible_end,
                    'type': 'audible',
                    'keep': True
                })
    
    # Handle audible segment after last silence (if any)
    # Check if we need to add an audible segment at the end
    if ends and ends[-1] < duration:
        # Check if the last segment reaches the end
        if not all_segments or all_segments[-1]['end'] < duration:
            # Determine the start of the final audible segment
            if all_segments and all_segments[-1]['type'] == 'audible':
                # Extend the last audible segment to the end
                all_segments[-1]['end'] = duration
            else:
                # Add a new audible segment from last silence end to video end
                all_segments.append({
                    'start': ends[-1],
                    'end': duration,
                    'type': 'audible',
                    'keep': True
                })
    
    # Apply padding to audible segments (extend them into adjacent silence)
    # This adjusts the boundaries of both audible and silent segments
    if pad_before > 0 or pad_after > 0:
        # First pass: calculate padded boundaries for audible segments
        padded_audible = {}
        for i, seg in enumerate(all_segments):
            if seg['type'] == 'audible':
                # Calculate how much we can extend this audible segment
                # Extend backward (pad_before) - but don't go before trim_start or into previous segment
                extend_back = pad_before
                if i > 0:
                    # Can't extend before previous segment's end
                    extend_back = min(extend_back, seg['start'] - all_segments[i-1]['end'])
                padded_start = max(trim_start, seg['start'] - extend_back)
                
                # Extend forward (pad_after) - but don't go beyond duration or into next segment
                extend_forward = pad_after
                if i + 1 < len(all_segments):
                    # Can't extend beyond next segment's start
                    extend_forward = min(extend_forward, all_segments[i+1]['start'] - seg['end'])
                padded_end = min(duration, seg['end'] + extend_forward)
                
                padded_audible[i] = {'start': padded_start, 'end': padded_end}
        
        # Second pass: rebuild segments with adjusted boundaries
        adjusted_segments = []
        for i, seg in enumerate(all_segments):
            if seg['type'] == 'audible':
                # Use padded boundaries
                if i in padded_audible:
                    adjusted_segments.append({
                        'start': padded_audible[i]['start'],
                        'end': padded_audible[i]['end'],
                        'type': 'audible',
                        'keep': True
                    })
            else:
                # Silent segment - adjust boundaries based on adjacent padded audible segments
                silent_start = seg['start']
                silent_end = seg['end']
                
                # Check if previous segment (audible) extends into this silence
                if i > 0 and i-1 in padded_audible:
                    prev_audible_end = padded_audible[i-1]['end']
                    if prev_audible_end > silent_start:
                        silent_start = min(silent_end, prev_audible_end)
                
                # Check if next segment (audible) extends into this silence
                if i + 1 < len(all_segments) and i+1 in padded_audible:
                    next_audible_start = padded_audible[i+1]['start']
                    if next_audible_start < silent_end:
                        silent_end = max(silent_start, next_audible_start)
                
                # Only add silent segment if it still has positive duration
                if silent_end > silent_start:
                    adjusted_segments.append({
                        'start': silent_start,
                        'end': silent_end,
                        'type': 'silent',
                        'keep': False
                    })
        
        all_segments = adjusted_segments

    # Count segments by type
    audible_count = sum(1 for seg in all_segments if seg['type'] == 'audible')
    silent_count = sum(1 for seg in all_segments if seg['type'] == 'silent')
    
    status_callback(f"🔍 Found {audible_count} audible segments and {silent_count} silent segments.\n")
    
    return all_segments


def validate_segments(segments: List[Tuple[float, float]], duration: float, 
                     min_segment_length: float = 0.1) -> List[Tuple[float, float]]:
    """
    Validate and clean up audio segments.
    
    This function validates a list of segments to ensure they are reasonable
    and removes any segments that are too short or invalid.
    
    Args:
        segments: List of (start_time, end_time) tuples
        duration: Total video duration in seconds
        min_segment_length: Minimum length for a valid segment in seconds
        
    Returns:
        List of validated segments
        
    Example:
        segments = [(0.0, 10.0), (10.5, 10.6), (15.0, 20.0)]  # Middle segment too short
        valid = validate_segments(segments, 30.0, 0.5)
        # Returns: [(0.0, 10.0), (15.0, 20.0)]  # Short segment removed
    """
    validated_segments = []
    
    for start, end in segments:
        # Check if segment has positive duration
        if end <= start:
            continue
            
        # Check if segment is long enough
        if (end - start) < min_segment_length:
            continue
            
        # Check if segment is within video bounds
        if start < 0 or end > duration:
            continue
            
        # Segment is valid
        validated_segments.append((start, end))
    
    return validated_segments


def merge_adjacent_segments(segments: List[Tuple[float, float]], 
                          merge_threshold: float = 0.1) -> List[Tuple[float, float]]:
    """
    Merge segments that are very close together.
    
    This function combines segments that are separated by very small gaps,
    which often represent brief pauses rather than true silence.
    
    Args:
        segments: List of (start_time, end_time) tuples
        merge_threshold: Maximum gap between segments to merge (seconds)
        
    Returns:
        List of merged segments
        
    Example:
        segments = [(0.0, 10.0), (10.05, 15.0), (15.2, 20.0)]
        merged = merge_adjacent_segments(segments, 0.1)
        # Returns: [(0.0, 15.0), (15.2, 20.0)]  # First two merged
    """
    if not segments:
        return []
    
    # Sort segments by start time
    sorted_segments = sorted(segments)
    merged_segments = [sorted_segments[0]]  # Start with first segment
    
    for current_start, current_end in sorted_segments[1:]:
        last_start, last_end = merged_segments[-1]
        
        # Check if segments are close enough to merge
        gap = current_start - last_end
        if gap <= merge_threshold:
            # Merge segments by extending the last one
            merged_segments[-1] = (last_start, current_end)
        else:
            # Keep segments separate
            merged_segments.append((current_start, current_end))
    
    return merged_segments


def calculate_total_audible_time(segments: List[Tuple[float, float]]) -> float:
    """
    Calculate total duration of all audible segments.
    
    This function sums up all the segment durations to give the total
    amount of audible content in the video.
    
    Args:
        segments: List of (start_time, end_time) tuples
        
    Returns:
        Total audible time in seconds
        
    Example:
        segments = [(0.0, 10.0), (15.0, 20.0), (25.0, 30.0)]
        total = calculate_total_audible_time(segments)
        # Returns: 20.0 (10 + 5 + 5 seconds)
    """
    return sum(end - start for start, end in segments)


def get_silence_percentage(segments: List[Tuple[float, float]], duration: float) -> float:
    """
    Calculate what percentage of the video is silence.
    
    This function determines how much of the video will be removed
    by calculating the percentage of time that is silence.
    
    Args:
        segments: List of audible segments
        duration: Total video duration
        
    Returns:
        Percentage of video that is silence (0.0 to 100.0)
        
    Example:
        segments = [(0.0, 10.0), (15.0, 20.0)]  # 15 seconds audible out of 30
        percentage = get_silence_percentage(segments, 30.0)
        # Returns: 50.0 (50% silence)
    """
    if duration <= 0:
        return 0.0
    
    audible_time = calculate_total_audible_time(segments)
    silence_time = duration - audible_time
    return (silence_time / duration) * 100.0
