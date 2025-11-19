"""
Performance test script for comparing Whisper model speeds.

Tests transcription speed of different Whisper models (tiny vs base) on a real video file.
"""

import os
import time
from pathlib import Path
from video_production_app.ai_analysis.transcriber import transcribe_segments
from video_production_app.config import AI_ANALYSIS_SETTINGS

# Video path - EDIT THIS to point to your test video file
VIDEO_PATH = r"E:\silance-cutter_github\.test_video.mp4"


def create_test_segments(video_duration: float = 60.0) -> list:
    """
    Create test segments for transcription.
    
    Creates segments covering the first portion of the video for performance testing.
    
    Args:
        video_duration: Maximum duration to transcribe (default: 60 seconds)
        
    Returns:
        List of segment dictionaries
    """
    segments = []
    segment_length = 10.0  # 10-second segments
    current_time = 0.0
    
    while current_time < video_duration:
        segments.append({
            'start': current_time,
            'end': min(current_time + segment_length, video_duration),
            'type': 'audible',
            'keep': True
        })
        current_time += segment_length
    
    return segments


def measure_transcription(model_name: str, segments: list) -> float:
    """
    Measure transcription time for a specific Whisper model.
    
    Args:
        model_name: Whisper model name ('tiny', 'base', 'small', 'medium', 'large')
        segments: List of segment dictionaries to transcribe
        
    Returns:
        Duration in seconds
    """
    print(f"--- Testing model: {model_name} ---")
    
    # Record start time
    start_time = time.time()
    
    try:
        # Call transcribe_segments with the specified model
        transcripts = transcribe_segments(
            video_path=VIDEO_PATH,
            segments=segments,
            model_size=model_name,
            ffmpeg_path="",  # Use system PATH
            status_callback=None,  # Suppress status messages for cleaner output
            progress_callback=None
        )
        
        # Record end time
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"   Time taken: {duration:.2f} seconds")
        print(f"   Segments transcribed: {len(transcripts)}")
        
        return duration
        
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        return float('inf')  # Return infinity to indicate failure


def main():
    """Run the performance comparison test."""
    
    print("=" * 80)
    print("WHISPER MODEL PERFORMANCE TEST")
    print("=" * 80)
    print()
    
    # Check if video file exists
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ Error: Video file not found at: {VIDEO_PATH}")
        print("   Please edit VIDEO_PATH in this script to point to your test video.")
        return
    
    print(f"Video file: {VIDEO_PATH}")
    print(f"File size: {os.path.getsize(VIDEO_PATH) / (1024 * 1024):.2f} MB")
    print()
    
    # Create test segments (first 60 seconds of video)
    test_segments = create_test_segments(video_duration=60.0)
    print(f"Test segments: {len(test_segments)} segments covering 0-60 seconds")
    print()
    
    # Run performance tests
    print("Starting transcription performance tests...")
    print()
    
    # Test tiny model
    tiny_time = measure_transcription("tiny", test_segments)
    print()
    
    # Test base model
    base_time = measure_transcription("base", test_segments)
    print()
    
    # Calculate results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    
    if tiny_time == float('inf') or base_time == float('inf'):
        print("❌ One or more tests failed. Cannot calculate speedup.")
        return
    
    # Determine winner
    if tiny_time < base_time:
        winner = "tiny"
        speedup = base_time / tiny_time
    else:
        winner = "base"
        speedup = tiny_time / base_time
    
    print(f"Tiny model time:  {tiny_time:.2f} seconds")
    print(f"Base model time:  {base_time:.2f} seconds")
    print()
    print(f"Winner: {winner.upper()}")
    print(f"Speedup: {speedup:.2f}x faster")
    print()
    
    # Additional statistics
    time_difference = abs(tiny_time - base_time)
    print(f"Time difference: {time_difference:.2f} seconds")
    
    if tiny_time < base_time:
        print(f"Tiny is {speedup:.2f}x faster but may have lower accuracy")
    else:
        print(f"Base is {speedup:.2f}x faster and typically has better accuracy")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()

