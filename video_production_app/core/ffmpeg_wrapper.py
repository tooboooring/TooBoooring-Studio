"""
FFmpeg and FFprobe wrapper functions for Video Production App.

This module provides a clean interface to FFmpeg and FFprobe command-line tools.
It handles all the low-level details of running FFmpeg commands, parsing output,
and error handling, making it easy for other parts of the application to use.

Key functions:
- get_available_encoders: Detect available hardware encoders
- get_audio_tracks: Scan video files for audio streams
- get_video_duration: Get video duration information
- analyze_audio_track_content: Analyze audio levels in tracks
- parse_ffmpeg_progress: Parse FFmpeg progress output for status updates

All functions include comprehensive error handling and user-friendly status messages.
"""

import os
import re
import subprocess
import json
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any

from ..config import ENCODER_OPTIONS


def get_available_encoders(ffmpeg_path: str, status_callback: Callable[[str], None]) -> List[str]:
    """Detects all available hardware and software encoders from our list."""
    ffmpeg_executable = ffmpeg_path or "ffmpeg"
    status_callback("🔍 Detecting available GPU encoders...\n")
    found_encoders = []

    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        # Run ffmpeg -encoders to get a list of all encoders
        result = subprocess.run(
            [str(ffmpeg_executable), "-encoders"], 
            capture_output=True, 
            text=True, 
            check=True, 
            encoding='utf-8', 
            errors='ignore', 
            startupinfo=startupinfo
        )
        available_encoders_output = result.stdout
        
        # Debug: Log a sample of the output to see format
        status_callback(f"📋 FFmpeg encoder list length: {len(available_encoders_output)} chars\n")
        
        # Check our ENCODER_OPTIONS list against the ffmpeg output
        for display_name, (encoder_name, _) in ENCODER_OPTIONS.items():
            if display_name == "Automatic (Best GPU)":
                continue # Skip this, it's a special option
            
            # Use regex to find the encoder in the output
            # FFmpeg format: " V....D h264_nvenc           NVIDIA NVENC H.264 encoder"
            # Pattern: V followed by 5 flag characters, then whitespace, then encoder name
            # The flags can be dots (.) or letters (A-Z)
            pattern = r"^\s*V[.A-Z]{5}\s+" + re.escape(encoder_name) + r"(\s|$)"
            if re.search(pattern, available_encoders_output, re.MULTILINE):
                found_encoders.append(display_name)
                status_callback(f"  ✓ Found: {display_name} ({encoder_name})\n")
            else:
                # Try simpler pattern - just V followed by flags and encoder name (no start anchor)
                alt_pattern = r"V[.A-Z]{5}\s+" + re.escape(encoder_name) + r"(\s|$)"
                if re.search(alt_pattern, available_encoders_output, re.MULTILINE):
                    found_encoders.append(display_name)
                    status_callback(f"  ✓ Found: {display_name} ({encoder_name}) [alt pattern]\n")
                else:
                    # Even simpler: just check if encoder name appears after "V" flag pattern
                    # This is the most permissive check
                    simple_pattern = r"V[.A-Z]+\s+" + re.escape(encoder_name)
                    if re.search(simple_pattern, available_encoders_output, re.MULTILINE):
                        found_encoders.append(display_name)
                        status_callback(f"  ✓ Found: {display_name} ({encoder_name}) [simple pattern]\n")
                    else:
                        # Debug: Check if encoder name appears at all
                        if encoder_name in available_encoders_output:
                            status_callback(f"  ⚠ {encoder_name} found in output but pattern didn't match\n")
                            # Try to find the line with this encoder
                            lines = available_encoders_output.split('\n')
                            for line in lines:
                                if encoder_name in line:
                                    status_callback(f"     Sample line: {line[:80]}\n")
                        else:
                            status_callback(f"  ✗ Not found: {encoder_name}\n")
        
        if "CPU (x264)" not in found_encoders:
            # Always add CPU as a fallback
            found_encoders.append("CPU (x264)")

        if len(found_encoders) > 1:
             status_callback(f"✅ Found {len(found_encoders) - 1} compatible hardware encoder(s).\n")
        else:
             status_callback("⚠️ No compatible hardware encoder found. Will use CPU.\n")

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        status_callback(f"❌ Could not run FFmpeg to detect encoders: {e}\n")
        if "CPU (x264)" not in found_encoders:
            found_encoders.append("CPU (x264)")
    
    # Always add "Automatic" as the first option
    found_encoders.insert(0, "Automatic (Best GPU)")
    
    return found_encoders


def get_audio_tracks(video_file: Path, ffprobe_path: str, status_callback: Callable[[str], None]) -> List[Dict[str, Any]]:
    """
    Use FFprobe to find all audio streams in a video file with detailed information.
    
    This function analyzes a video file and extracts information about all audio
    tracks, including codec, language, channel configuration, sample rate, and bitrate.
    
    Args:
        video_file: Path to the video file to analyze
        ffprobe_path: Path to FFprobe executable (empty string uses system PATH)
        status_callback: Function to call with status messages for the user
        
    Returns:
        List of dictionaries, each containing audio track information:
        - name: Display name for the track
        - index: Track index in the file
        - codec: Audio codec name
        - language: Language code (e.g., "eng", "und" for unknown)
        - channels: Number of audio channels
        - channel_str: Human-readable channel description (mono, stereo, 5.1, etc.)
        - sample_rate: Sample rate in kHz
        - bitrate: Bitrate in kbps
        - bitrate_raw: Raw bitrate value
        
    Example:
        tracks = get_audio_tracks(Path("video.mp4"), "", print)
        # Returns: [{"name": "Track 0 (aac, eng)", "index": 0, "codec": "aac", ...}]
    """
    # Tell user what we're doing
    status_callback(f"🔎 Scanning for audio tracks in {video_file.name}...\n")
    
    # Use provided path or default to system PATH
    ffprobe_executable = ffprobe_path or "ffprobe"
    
    # Build FFprobe command to get audio stream information
    cmd = [
        str(ffprobe_executable), 
        "-v", "error",  # Only show errors, not warnings
        "-show_streams",  # Show stream information
        "-select_streams", "a",  # Only audio streams
        "-of", "json",  # Output format: JSON
        str(video_file)
    ]
    
    try:
        # Set up Windows-specific startup info
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        # Run FFprobe command
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            encoding='utf-8', 
            errors='ignore', 
            startupinfo=startupinfo
        )
        
        # Parse JSON output
        streams = json.loads(result.stdout).get("streams", [])
        audio_tracks = []
        
        # Process each audio stream
        for stream in streams:
            # Extract basic information
            track_index = stream.get("index")
            codec_name = stream.get("codec_name", "unknown")
            language = stream.get("tags", {}).get("language", "und")  # "und" = undefined/unknown
            channels = stream.get("channels", "?")
            sample_rate = stream.get("sample_rate", "?")
            bit_rate = stream.get("bit_rate", "0")
            
            # Convert channel count to human-readable format
            if channels == 1:
                channel_str = "mono"
            elif channels == 2:
                channel_str = "stereo"
            elif channels == 6:
                channel_str = "5.1"  # Surround sound
            elif channels == 8:
                channel_str = "7.1"  # Surround sound with rear speakers
            else:
                channel_str = f"{channels}ch"  # Generic format
            
            # Convert bitrate to kbps
            try:
                bitrate_kbps = int(bit_rate) // 1000
                bitrate_str = f"{bitrate_kbps}kbps" if bitrate_kbps > 0 else "N/A"
            except (ValueError, TypeError):
                bitrate_str = "N/A"
            
            # Convert sample rate to kHz
            try:
                sample_rate_khz = int(sample_rate) // 1000
                sample_rate_str = f"{sample_rate_khz}kHz"
            except (ValueError, TypeError):
                sample_rate_str = "?"
            
            # Create display name
            language_part = f", {language}" if language != 'und' else ''
            name = f"Track {track_index} ({codec_name}{language_part})"
            
            # Add track information to list
            audio_tracks.append({
                "name": name,
                "index": track_index,
                "codec": codec_name,
                "language": language,
                "channels": channels,
                "channel_str": channel_str,
                "sample_rate": sample_rate_str,
                "bitrate": bitrate_str,
                "bitrate_raw": int(bit_rate) if bit_rate.isdigit() else 0
            })
        
        # Report results to user
        if not audio_tracks:
            status_callback("⚠️ No audio tracks found in this file.\n")
        else:
            status_callback(f"✅ Found {len(audio_tracks)} audio track(s).\n")
            
        return audio_tracks

    except FileNotFoundError:
        # FFprobe not found
        status_callback(f"❌ Error: '{ffprobe_executable}' not found.\n")
        status_callback("   Please place ffprobe.exe next to the app, or add it to your system's PATH.\n")
        return []
        
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        # FFprobe failed or output couldn't be parsed
        status_callback(f"❌ Error scanning for audio tracks: {e}\n")
        return []


def get_video_duration(video_file: Path, ffprobe_path: str, status_callback: Callable[[str], None]) -> float:
    """
    Get video duration in seconds using FFprobe.
    
    This function extracts the total duration of a video file using FFprobe.
    It's used throughout the application to know how long videos are for
    processing, timeline display, and progress calculations.
    
    Args:
        video_file: Path to the video file
        ffprobe_path: Path to FFprobe executable (empty string uses system PATH)
        status_callback: Function to call with error messages
        
    Returns:
        Duration in seconds as a float, or 0.0 if there was an error
        
    Example:
        duration = get_video_duration(Path("video.mp4"), "", print)
        # Returns: 125.5 (for a 2 minute 5.5 second video)
    """
    # Use provided path or default to system PATH
    ffprobe_executable = ffprobe_path or "ffprobe"
    
    # Build FFprobe command to get duration
    cmd = [
        str(ffprobe_executable), 
        "-v", "error",  # Only show errors
        "-show_entries", "format=duration",  # Show only duration
        "-of", "default=noprint_wrappers=1:nokey=1",  # Just the number
        str(video_file)
    ]
    
    try:
        # Set up Windows-specific startup info
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        # Run FFprobe command
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            encoding='utf-8', 
            errors='ignore', 
            startupinfo=startupinfo
        )
        
        # Convert output to float
        return float(result.stdout.strip())
        
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError) as e:
        # Something went wrong - report error and return 0
        status_callback(f"❌ Error getting duration: {e}\n")
        return 0.0


def analyze_audio_track_content(video_file: Path, track_index: int, ffmpeg_path: str) -> Dict[str, Any]:
    """
    Analyze if an audio track has content or is silent using FFmpeg's volumedetect filter.
    
    This function analyzes the first 10 seconds of an audio track to determine
    if it contains actual audio content or is silent/empty. This is useful for
    identifying which tracks to use for silence detection.
    
    Args:
        video_file: Path to the video file
        track_index: Index of the audio track to analyze
        ffmpeg_path: Path to FFmpeg executable (empty string uses system PATH)
        
    Returns:
        Dictionary containing analysis results:
        - is_silent: Boolean indicating if track is silent
        - mean_volume: Average volume in dB (None if not detected)
        - max_volume: Maximum volume in dB (None if not detected)
        - status: Human-readable status description
        
    Example:
        analysis = analyze_audio_track_content(Path("video.mp4"), 0, "")
        # Returns: {"is_silent": False, "mean_volume": -25.5, "max_volume": -15.2, "status": "Normal Audio"}
    """
    # Use provided path or default to system PATH
    ffmpeg_executable = ffmpeg_path or "ffmpeg"
    
    # Build FFmpeg command to analyze audio levels
    # We only analyze first 10 seconds for speed
    cmd = [
        str(ffmpeg_executable), 
        "-hide_banner",  # Don't show FFmpeg banner
        "-i", str(video_file),  # Input file
        "-map", f"0:{track_index}",  # Select specific audio track
        "-af", "volumedetect",  # Use volume detection filter
        "-f", "null",  # No output file needed
        "-t", "10",  # Only analyze first 10 seconds
        "-"  # Output to null
    ]
    
    try:
        # Set up Windows-specific startup info
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
        
        # Parse volumedetect output from stderr
        output = result.stderr
        mean_volume = None
        max_volume = None
        
        # Look for volume information in FFmpeg output
        mean_match = re.search(r'mean_volume:\s*(-?\d+\.?\d*)\s*dB', output)
        max_match = re.search(r'max_volume:\s*(-?\d+\.?\d*)\s*dB', output)
        
        if mean_match:
            mean_volume = float(mean_match.group(1))
        if max_match:
            max_volume = float(max_match.group(1))
        
        # Determine if track is silent based on volume levels
        is_silent = False
        status = "Has Audio"
        
        if mean_volume is None or max_volume is None:
            # No volume data detected - likely no audio
            is_silent = True
            status = "No Audio Data"
        elif mean_volume < -70 or max_volume < -60:
            # Very quiet - likely silent track
            is_silent = True
            status = "Silent/Empty"
        elif mean_volume < -40:
            # Quiet but has audio
            status = "Quiet Audio"
        elif mean_volume < -20:
            # Normal volume level
            status = "Normal Audio"
        else:
            # Loud audio
            status = "Loud Audio"
        
        return {
            "is_silent": is_silent,
            "mean_volume": mean_volume,
            "max_volume": max_volume,
            "status": status
        }
    
    except Exception:
        # If anything goes wrong, assume track has audio
        return {
            "is_silent": False,
            "mean_volume": None,
            "max_volume": None,
            "status": "Unknown"
        }


def parse_ffmpeg_progress(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse FFmpeg progress output to extract timing and speed information.
    
    This function looks at FFmpeg's progress output and extracts useful
    information like current processing time and processing speed. This
    is used to show progress bars and estimated completion times.
    
    Args:
        line: A line of FFmpeg output to parse
        
    Returns:
        Dictionary with progress information, or None if no progress data found:
        - time: Current processing time in seconds
        - speed: Processing speed multiplier (e.g., 2.5x means 2.5x real-time)
        
    Example:
        progress = parse_ffmpeg_progress("time=00:01:25.50 speed=2.5x")
        # Returns: {"time": 85.5, "speed": 2.5}
    """
    progress_data = {}
    
    # Look for time information in format "time=HH:MM:SS.ss"
    if "time=" in line:
        time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
        if time_match:
            hours, minutes, seconds = time_match.groups()
            # Convert to total seconds
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            progress_data['time'] = total_seconds
    
    # Look for speed information in format "speed=X.Xx"
    if "speed=" in line:
        speed_match = re.search(r'speed=\s*(\d+\.?\d*)x', line)
        if speed_match:
            progress_data['speed'] = float(speed_match.group(1))
    
    # Return data only if we found something useful
    return progress_data if progress_data else None
