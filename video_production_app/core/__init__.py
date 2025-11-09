"""
Core business logic module for Video Production App.

This module contains all the business logic separated from the user interface:
- ffmpeg_wrapper: FFmpeg and FFprobe command execution
- silence_detector: Audio silence detection algorithms
- video_processor: Main video processing logic
- settings_manager: Configuration and settings persistence

These modules handle the core functionality without any UI dependencies,
making them easy to test and reuse.
"""
