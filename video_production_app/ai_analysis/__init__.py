"""
AI Content Analysis Module for Video Production App.

This package provides AI-powered content analysis for video segments,
using local Whisper transcription and together.ai for semantic evaluation.

Modules:
- transcriber: Local Whisper transcription for audio segments
- context_builder: Extracts before/after context for segments
- ai_analyzer: together.ai API client with flexible prompt templates
- orchestrator: Pipeline coordinator for the full analysis workflow
"""

from .transcriber import transcribe_segments, transcribe_full_video
from .context_builder import build_context, ContextWindow
from .ai_analyzer import analyze_segment, SegmentDecision
from .orchestrator import analyze_content

__all__ = [
    'transcribe_segments',
    'transcribe_full_video',
    'build_context',
    'ContextWindow',
    'analyze_segment',
    'SegmentDecision',
    'analyze_content',
]

__version__ = '1.0.0'

