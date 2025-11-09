"""
Video processing logic for Video Production App.

This module contains the main video processing functionality that handles
silence removal, video trimming, and output generation. It coordinates
between silence detection, FFmpeg operations, and progress reporting.

Key functions:
- process_video_logic: Main video processing function with silence removal
- Complex filter generation for multi-track audio and video
- Progress monitoring and error handling
- Output file management and cleanup

This is the core processing engine that takes detected silence segments
and creates the final processed video with silence removed.
"""

import os
import shlex
import subprocess
from pathlib import Path
from datetime import timedelta
from typing import Callable, Optional, List, Dict, Any, Tuple

from .ffmpeg_wrapper import get_video_duration, parse_ffmpeg_progress
from .silence_detector import detect_silence, parse_segments


def process_video_logic(video_path: str, output_dir: str, output_format: str, video_params: str, 
                       all_audio_tracks: List[Dict[str, Any]], silence_track_index: int, 
                       ffmpeg_path: str, ffprobe_path: str, settings: Dict[str, Any],
                       status_callback: Callable[[str], None], 
                       progress_callback: Optional[Callable[[float, str, float], None]] = None,
                       trim_start: float = 0, trim_end: Optional[float] = None,
                       segments: Optional[List[Dict[str, Any]]] = None) -> None:
    """
    Process video with silence removal and optional trimming.
    
    This is the main video processing function that takes a video file and
    creates a new version with silence removed. It handles complex FFmpeg
    operations, multi-track audio, progress monitoring, and error handling.
    
    The function works in several steps:
    1. Set up output files and directories
    2. Get video duration and validate input
    3. Detect silence segments (if not provided)
    4. Build complex FFmpeg filter for video and audio processing
    5. Run FFmpeg with progress monitoring
    6. Clean up temporary files
    
    Args:
        video_path: Path to input video file
        output_dir: Directory where output file will be saved
        output_format: Output format (mp4, avi, etc.)
        video_params: FFmpeg video encoding parameters
        all_audio_tracks: List of audio track information dictionaries
        silence_track_index: Index of audio track to use for silence detection
        ffmpeg_path: Path to FFmpeg executable
        ffprobe_path: Path to FFprobe executable
        settings: Dictionary containing processing settings
        status_callback: Function to call with status messages
        progress_callback: Optional function to call with progress updates
        trim_start: Start time for processing (seconds)
        trim_end: End time for processing (seconds, None for full duration)
        segments: Pre-detected silence segments (None to detect automatically)
        
    Example:
        process_video_logic(
            video_path="input.mp4",
            output_dir="./output",
            output_format="mp4",
            video_params="-c:v h264_nvenc -crf 20",
            all_audio_tracks=[{"index": 0, "name": "Track 0"}],
            silence_track_index=0,
            ffmpeg_path="",
            ffprobe_path="",
            settings={"silence_db": -40, "silence_duration": 0.7},
            status_callback=print,
            progress_callback=lambda p, e, s: print(f"{p}% - {e}")
        )
    """
    # Convert paths to Path objects for easier handling
    video_file = Path(video_path)
    output_path = Path(output_dir)
    
    # Create temporary directory for processing files
    temp_dir = output_path / "temp_silence_cutter"
    temp_dir.mkdir(exist_ok=True)
    
    # Generate output filename
    output_file = output_path / f"{video_file.stem}_final.{output_format.lower()}"
    
    # Check if output file already exists
    if output_file.exists():
        status_callback(f"⏭️ Output file '{output_file.name}' already exists. Skipping.\n")
        return
    
    # Start processing
    status_callback("-" * 40 + "\n")
    status_callback(f"🎬 Starting processing for: {video_file.name}\n")
    
    # Get video duration
    duration = get_video_duration(video_file, ffprobe_path, status_callback)
    if duration == 0.0:
        status_callback("❌ Could not determine video duration. Aborting.\n")
        return
    
    # Calculate effective duration (considering trim_end)
    effective_duration = trim_end if trim_end is not None else duration
    
    # Detect silence segments if not provided
    if segments is None:
        status_callback("🔍 Detecting silence segments...\n")
        ffmpeg_log = detect_silence(video_file, silence_track_index, ffmpeg_path, settings, status_callback, trim_start, trim_end)
        segments = parse_segments(ffmpeg_log, effective_duration, settings, status_callback, trim_start)
    
    # Check if we have valid segments to process
    if not segments:
        status_callback("⚠️ No valid audible segments found. Skipping.\n")
        return
    
    # Extract ALL segments that should be kept (both audible and silent with keep=True)
    # This includes:
    # - All audible segments (always kept)
    # - Silent segments marked as "good" (keep=True, shown as gray)
    segments_to_keep = [
        (seg['start'], seg['end']) 
        for seg in segments 
        if seg.get('keep', True)  # Keep all segments with keep=True (audible + good silence)
    ]
    
    if not segments_to_keep:
        status_callback("⚠️ No segments to keep. Skipping.\n")
        return
    
    # Sort segments by start time to ensure chronological order
    segments_to_keep = sorted(segments_to_keep, key=lambda x: x[0])
    
    # Build FFmpeg filter for selecting segments to keep
    # This creates a filter like "between(t,0,10)+between(t,15,20)+between(t,25,30)"
    select_filter = "+".join([f"between(t,{s},{e})" for s, e in segments_to_keep])
    
    # Parse video and audio parameters
    video_args = shlex.split(video_params)
    
    # Set audio parameters based on output format
    if output_format.lower() == "mp4":
        audio_params = "-c:a aac -b:a 192k"  # AAC codec for MP4
    else:
        audio_params = "-c:a pcm_s16le"  # Uncompressed audio for other formats
    audio_args = shlex.split(audio_params)
    
    # Build complex filter for video and audio processing
    filter_complex_parts = []
    map_args = []
    
    # Video filter: select audible segments and fix timestamps
    video_filter = f"[0:v]select='{select_filter}',setpts=N/FRAME_RATE/TB[v]"
    filter_complex_parts.append(video_filter)
    map_args.append("[v]")
    
    # Audio filters: process each audio track separately
    for i, track in enumerate(all_audio_tracks):
        stream_index = track['index']
        # Create audio filter for this track
        audio_filter = f"[0:{stream_index}]aselect='{select_filter}',asetpts=N/SR/TB[a{i}]"
        filter_complex_parts.append(audio_filter)
        map_args.append(f"[a{i}]")
    
    # Join all filters with semicolons
    filter_complex = ";".join(filter_complex_parts)
    
    # Build base FFmpeg command
    ffmpeg_executable = ffmpeg_path or "ffmpeg"
    base_cmd = [str(ffmpeg_executable), "-y", "-hide_banner"]  # -y = overwrite output files
    
    # Add progress reporting if callback provided
    if progress_callback:
        base_cmd.extend(["-progress", "pipe:1", "-stats_period", "0.5"])
    
    # Add input file
    base_cmd.extend(["-i", str(video_file)])
    
    # Handle very long filter strings by using a temporary file
    temp_filter_file = None
    filter_length_threshold = settings.get("filter_length_threshold", 4096)
    
    if len(filter_complex) > filter_length_threshold:
        status_callback("🛠️ Filter string is very long. Using a temporary script file.\n")
        temp_filter_file = temp_dir / f"{video_file.stem}_filter.txt"
        temp_filter_file.write_text(filter_complex, encoding='utf-8')
        filter_cmd = ["-filter_complex_script", str(temp_filter_file)]
    else:
        filter_cmd = ["-filter_complex", filter_complex]
    
    # Build mapping arguments for output
    # Convert ["[v]", "[a0]", "[a1]"] to ["-map", "[v]", "-map", "[a0]", "-map", "[a1]"]
    final_map_args = []
    for map_arg in map_args:
        final_map_args.extend(["-map", map_arg])
    
    # Add pixel format for MP4 compatibility
    if output_format.lower() == "mp4":
        video_args.extend(["-pix_fmt", "yuv420p"])
    
    # Combine all command parts
    cmd = base_cmd + filter_cmd + final_map_args + video_args + audio_args + [str(output_file)]
    
    status_callback("⚙️ Running FFmpeg... This may take a while.\n")
    
    try:
        # Set up Windows-specific startup info
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        if progress_callback:
            # Run with progress monitoring
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                encoding='utf-8', 
                errors='ignore', 
                startupinfo=startupinfo
            )
            
            # Calculate total duration of all segments to keep
            total_duration = sum(end - start for start, end in segments_to_keep)
            
            # Monitor progress
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                    
                if output:
                    # Parse progress information
                    progress_data = parse_ffmpeg_progress(output)
                    if progress_data and 'time' in progress_data:
                        current_time = progress_data['time']
                        
                        # Calculate percentage complete
                        percentage = min(100, (current_time / total_duration) * 100) if total_duration > 0 else 0
                        speed = progress_data.get('speed', 0)
                        
                        # Calculate estimated time remaining
                        if speed > 0:
                            remaining_time = (total_duration - current_time) / speed
                            eta = str(timedelta(seconds=int(remaining_time)))
                        else:
                            eta = "Calculating..."
                        
                        # Call progress callback
                        progress_callback(percentage, eta, speed)
            
            # Wait for process to complete and check return code
            return_code = process.wait()
            if return_code != 0:
                stderr = process.stderr.read()
                raise subprocess.CalledProcessError(return_code, cmd, stderr=stderr)
        else:
            # Run without progress monitoring
            subprocess.run(
                cmd, 
                check=True, 
                capture_output=True, 
                text=True, 
                encoding='utf-8', 
                errors='ignore', 
                startupinfo=startupinfo
            )
        
        # Success!
        status_callback(f"✅ Successfully created: {output_file.name}\n")
        status_callback(f"📍 Saved to: {output_file}\n")
        
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # Handle FFmpeg errors
        status_callback(f"❌ FFmpeg failed for {video_file.name}!\n")
        if isinstance(e, subprocess.CalledProcessError):
            status_callback(f"   FFmpeg stderr:\n{e.stderr}\n")
        else:
            status_callback(f"   Error: '{ffmpeg_executable}' not found.\n")
            
    finally:
        # Clean up temporary files
        if temp_filter_file and temp_filter_file.exists():
            temp_filter_file.unlink()
        
        # Remove temporary directory if empty
        try:
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                temp_dir.rmdir()
        except OSError:
            pass  # Ignore cleanup errors


def estimate_processing_time(segments: List[Tuple[float, float]], 
                           video_duration: float, 
                           encoder_speed: float = 1.0) -> float:
    """
    Estimate how long video processing will take.
    
    This function calculates an estimated processing time based on the
    amount of content to process and the expected encoder speed.
    
    Args:
        segments: List of audible segments to process
        video_duration: Total video duration in seconds
        encoder_speed: Expected encoder speed multiplier (1.0 = real-time)
        
    Returns:
        Estimated processing time in seconds
        
    Example:
        segments = [(0, 10), (15, 20), (25, 30)]  # 20 seconds of content
        time = estimate_processing_time(segments, 30.0, 2.0)  # 2x speed
        # Returns: 10.0 (20 seconds / 2x speed)
    """
    if not segments or encoder_speed <= 0:
        return 0.0
    
    # Calculate total content duration
    total_content = sum(end - start for start, end in segments)
    
    # Estimate processing time
    estimated_time = total_content / encoder_speed
    
    return estimated_time


def validate_output_settings(output_format: str, video_params: str) -> Tuple[bool, str]:
    """
    Validate output format and video parameters for compatibility.
    
    This function checks if the output format and video parameters
    are compatible and will produce valid output files.
    
    Args:
        output_format: Desired output format (mp4, avi, etc.)
        video_params: FFmpeg video encoding parameters
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        valid, error = validate_output_settings("mp4", "-c:v h264_nvenc")
        # Returns: (True, "")
    """
    # Check output format
    valid_formats = ["mp4", "avi", "mov", "mkv", "webm"]
    if output_format.lower() not in valid_formats:
        return False, f"Unsupported output format: {output_format}"
    
    # Check for basic video codec
    if "-c:v" not in video_params:
        return False, "No video codec specified in parameters"
    
    # Check for common issues
    if "mp4" in output_format.lower() and "h264" not in video_params.lower():
        return False, "MP4 format requires H.264 video codec"
    
    return True, ""


def get_processing_summary(segments: List[Tuple[float, float]], 
                          video_duration: float) -> Dict[str, Any]:
    """
    Generate a summary of what will be processed.
    
    This function analyzes the segments and provides statistics
    about what will be kept and removed from the video.
    
    Args:
        segments: List of audible segments
        video_duration: Total video duration
        
    Returns:
        Dictionary with processing statistics
        
    Example:
        summary = get_processing_summary([(0, 10), (15, 20)], 30.0)
        # Returns: {"total_segments": 2, "audible_time": 15.0, "silence_percentage": 50.0}
    """
    if not segments or video_duration <= 0:
        return {
            "total_segments": 0,
            "audible_time": 0.0,
            "silence_percentage": 100.0,
            "compression_ratio": 0.0
        }
    
    # Calculate statistics
    total_segments = len(segments)
    audible_time = sum(end - start for start, end in segments)
    silence_time = video_duration - audible_time
    silence_percentage = (silence_time / video_duration) * 100.0
    compression_ratio = (audible_time / video_duration) * 100.0
    
    return {
        "total_segments": total_segments,
        "audible_time": audible_time,
        "silence_time": silence_time,
        "silence_percentage": silence_percentage,
        "compression_ratio": compression_ratio,
        "original_duration": video_duration,
        "final_duration": audible_time
    }
