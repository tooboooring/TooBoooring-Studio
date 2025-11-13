"""
Configuration constants and settings for Video Production App.

This module contains all the default settings, encoder options, and application
configuration that can be easily modified without touching the main code.

Key components:
- DEFAULT_SETTINGS: Default silence detection parameters
- ENCODER_OPTIONS: Available video encoders with their FFmpeg parameters
- Application metadata and version information

These settings are used throughout the application to maintain consistency
and allow easy customization of behavior.
"""

# Default settings for silence detection
# These values are used when no user preferences are saved
DEFAULT_SETTINGS = {
    # Silence detection threshold in decibels (dB)
    # Lower values = more sensitive detection (e.g., -50 dB detects quieter sounds)
    # Higher values = less sensitive detection (e.g., -30 dB only detects loud sounds)
    "silence_db": -40,  # -40 dB is a good balance for most content
    
    # Minimum duration of silence to be detected (in seconds)
    # Shorter durations detect brief pauses, longer durations ignore short gaps
    "silence_duration": 0.7,  # 0.7 seconds catches most natural pauses
    
    # Padding before silence segments (in seconds)
    # Adds extra time before each silence to ensure we don't cut off speech
    "pad_before": 0.1,  # 0.1 seconds prevents cutting off word beginnings
    
    # Padding after silence segments (in seconds)
    # Adds extra time after each silence to ensure smooth transitions
    "pad_after": 0.0,  # Usually not needed, but can help with audio transitions
    
    # Minimum length for audio segments to keep (in samples)
    # Very short segments are often artifacts and should be filtered out
    "filter_length_threshold": 4096  # About 0.1 seconds at 44.1kHz
}

# Available video encoders with their FFmpeg parameters
# Each encoder has different quality/speed tradeoffs and hardware requirements
ENCODER_OPTIONS = {
    # NVIDIA GPU encoders (requires NVIDIA GPU with NVENC support)
    "NVIDIA (H.264)": (
        "h264_nvenc",  # FFmpeg encoder name
        "-c:v h264_nvenc -rc constqp -qp 20 -preset slow"  # Quality settings
    ),
    "NVIDIA (HEVC)": (
        "hevc_nvenc",  # HEVC provides better compression than H.264
        "-c:v hevc_nvenc -rc constqp -qp 20 -preset slow"
    ),
    
    # AMD GPU encoders (requires AMD GPU with AMF support)
    "AMD (H.264)": (
        "h264_amf",
        "-c:v h264_amf -quality balanced -rc cqp -qp_p 20 -qp_i 20"
    ),
    "AMD (HEVC)": (
        "hevc_amf",
        "-c:v hevc_amf -quality balanced -rc cqp -qp_p 20 -qp_i 20"
    ),
    
    # Intel GPU encoders (requires Intel GPU with Quick Sync support)
    "Intel (H.264)": (
        "h264_qsv",
        "-c:v h264_qsv -q 20 -preset slow"
    ),
    "Intel (HEVC)": (
        "hevc_qsv",
        "-c:v hevc_qsv -q 20 -preset slow"
    ),
    
    # CPU encoder (works on any system, but slower)
    "CPU (x264)": (
        "libx264",  # Software encoder, most compatible
        "-c:v libx264 -crf 20 -preset medium"  # CRF 20 = high quality
    ),
    
    # Automatic selection (will choose best available GPU encoder)
    "Automatic (Best GPU)": (
        "auto",  # Special marker for auto-selection
        ""  # Parameters will be determined at runtime
    )
}

# Application metadata
APP_NAME = "Video Production Suite"
APP_VERSION = "3.0.0"
APP_DESCRIPTION = "Professional video editing with silence detection and GPU acceleration"

# File extensions supported by the application
SUPPORTED_VIDEO_FORMATS = [
    ".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"
]

# Default output format when user doesn't specify
DEFAULT_OUTPUT_FORMAT = "mp4"

# Settings file name (maintains compatibility with existing installations)
SETTINGS_FILE_NAME = "video_cutter_settings.json"

# File validation limits (for security and stability)
FILE_LIMITS = {
    "max_file_size_mb": None,  # None = no limit (allow any file size)
    "max_waveform_samples": 1000000,  # Maximum samples for waveform display
    "max_segments": 10000  # Maximum number of segments to prevent memory issues
}

# UI Settings (can be customized by users)
UI_SETTINGS = {
    "timeline": {
        "max_zoom": 100.0,
        "min_zoom": 0.1,
        "waveform_height": 210,  # pixels
        "default_theme": "dark"
    },
    "performance": {
        "enable_waveform_cache": True,
        "cache_size_mb": 100,  # Maximum cache size
        "lazy_load_waveforms": True  # Load waveforms on demand
    }
}

# AI Content Analysis Settings
AI_ANALYSIS_SETTINGS = {
    # together.ai API configuration
    "api_key": "",  # User must provide their own API key
    "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",  # Default model
    "temperature": 0.7,  # LLM temperature (0.0-1.0)
    "max_tokens": 500,  # Maximum response tokens
    
    # Whisper transcription settings
    "whisper_model": "base",  # Options: 'tiny', 'base', 'small', 'medium', 'large'
    # Model sizes and memory requirements:
    # - tiny: ~1GB VRAM, fastest, lower accuracy
    # - base: ~1GB VRAM, good balance (recommended)
    # - small: ~2GB VRAM, better accuracy
    # - medium: ~5GB VRAM, very good accuracy
    # - large: ~10GB VRAM, best accuracy, slowest
    
    # Context window configuration
    "context_window_seconds": 30.0,  # How many seconds before/after to include
    
    # API rate limiting
    "api_delay_seconds": 0.5,  # Delay between API calls to avoid rate limits
    
    # Caching and performance
    "cache_transcriptions": True,  # Cache Whisper results
    "cache_ai_decisions": True,  # Cache AI analysis results
    "export_decisions_json": True,  # Export analysis to JSON for review
    
    # Prompt configuration (can be overridden in UI)
    "use_custom_prompt": False,  # Set to True to use custom prompt template
    "custom_prompt_template": None,  # Path to custom prompt file or template string
    
    # Content evaluation criteria (for reference in prompt design)
    "keep_criteria": [
        "Asides, jokes, moments of letting audience in",
        "Valuable insights or information",
        "Good storytelling and narrative flow",
        "Authentic connection with viewers"
    ],
    "flag_criteria": [
        "Technical difficulties or errors",
        "Filler words and meaningless sentences",
        "Self-aggrandizing or self-important rants",
        "Content that doesn't contribute value"
    ]
}