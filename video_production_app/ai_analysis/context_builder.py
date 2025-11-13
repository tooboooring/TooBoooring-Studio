"""
Context builder for AI analysis.

This module extracts surrounding context (before/after text) for each segment
to help the AI understand narrative flow and make better content decisions.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ContextWindow:
    """Represents a segment with its surrounding context."""
    segment_id: str
    start_time: float
    end_time: float
    current_text: str
    before_text: str
    after_text: str
    before_duration: float  # How much time before (in seconds)
    after_duration: float   # How much time after (in seconds)


def build_context(
    transcripts: Dict[str, Any],
    target_segment_id: str,
    segments: List[Dict[str, Any]],
    context_window_seconds: float = 30.0
) -> ContextWindow:
    """
    Build a context window for a specific segment.
    
    Extracts the text from surrounding segments (before and after) to provide
    the AI with narrative context for better decision-making.
    
    Args:
        transcripts: Dictionary mapping segment_id to TranscriptSegment objects
        target_segment_id: The segment ID to build context for
        segments: Original list of all segments (for timing information)
        context_window_seconds: How many seconds before/after to include
        
    Returns:
        ContextWindow object with current text and surrounding context
        
    Example:
        context = build_context(transcripts, "segment_5", segments, 30.0)
        # Returns context with text from 30s before and 30s after segment_5
    """
    # Get the target segment
    if target_segment_id not in transcripts:
        raise ValueError(f"Segment '{target_segment_id}' not found in transcripts")
    
    target_transcript = transcripts[target_segment_id]
    target_start = target_transcript.start_time
    target_end = target_transcript.end_time
    
    # Extract segment index from ID (assumes format "segment_N")
    try:
        target_idx = int(target_segment_id.split('_')[1])
    except (IndexError, ValueError):
        target_idx = -1
    
    # Collect before context
    before_text_parts = []
    before_duration = 0.0
    
    # Look backward through segments
    for i in range(target_idx - 1, -1, -1):
        seg_id = f"segment_{i}"
        if seg_id not in transcripts:
            continue
        
        seg_transcript = transcripts[seg_id]
        
        # Check if this segment is within the context window
        time_gap = target_start - seg_transcript.end_time
        if time_gap > context_window_seconds:
            break  # Too far back
        
        # Add to before context (prepend since we're going backwards)
        before_text_parts.insert(0, seg_transcript.text)
        before_duration = target_start - seg_transcript.start_time
    
    before_text = " ".join(before_text_parts)
    
    # Collect after context
    after_text_parts = []
    after_duration = 0.0
    
    # Look forward through segments
    for i in range(target_idx + 1, len(transcripts)):
        seg_id = f"segment_{i}"
        if seg_id not in transcripts:
            continue
        
        seg_transcript = transcripts[seg_id]
        
        # Check if this segment is within the context window
        time_gap = seg_transcript.start_time - target_end
        if time_gap > context_window_seconds:
            break  # Too far forward
        
        # Add to after context
        after_text_parts.append(seg_transcript.text)
        after_duration = seg_transcript.end_time - target_end
    
    after_text = " ".join(after_text_parts)
    
    # Create and return context window
    return ContextWindow(
        segment_id=target_segment_id,
        start_time=target_start,
        end_time=target_end,
        current_text=target_transcript.text,
        before_text=before_text,
        after_text=after_text,
        before_duration=before_duration,
        after_duration=after_duration
    )


def build_all_contexts(
    transcripts: Dict[str, Any],
    segments: List[Dict[str, Any]],
    context_window_seconds: float = 30.0
) -> Dict[str, ContextWindow]:
    """
    Build context windows for all transcribed segments.
    
    Args:
        transcripts: Dictionary of all TranscriptSegment objects
        segments: Original list of all segments
        context_window_seconds: Context window size in seconds
        
    Returns:
        Dictionary mapping segment_id to ContextWindow
    """
    contexts = {}
    
    for segment_id in transcripts.keys():
        try:
            context = build_context(
                transcripts,
                segment_id,
                segments,
                context_window_seconds
            )
            contexts[segment_id] = context
        except Exception as e:
            # Skip segments that fail to build context
            print(f"Warning: Failed to build context for {segment_id}: {e}")
            continue
    
    return contexts


def format_context_for_prompt(context: ContextWindow) -> str:
    """
    Format a context window for inclusion in an AI prompt.
    
    Args:
        context: ContextWindow object
        
    Returns:
        Formatted string suitable for LLM input
    """
    parts = []
    
    if context.before_text:
        parts.append(f"[PREVIOUS CONTEXT (from {context.before_duration:.1f}s before)]")
        parts.append(context.before_text)
        parts.append("")
    
    parts.append(f"[CURRENT SEGMENT ({context.start_time:.1f}s - {context.end_time:.1f}s)]")
    parts.append(context.current_text)
    parts.append("")
    
    if context.after_text:
        parts.append(f"[FOLLOWING CONTEXT (next {context.after_duration:.1f}s)]")
        parts.append(context.after_text)
    
    return "\n".join(parts)


def get_segment_statistics(contexts: Dict[str, ContextWindow]) -> Dict[str, Any]:
    """
    Get statistics about the context windows.
    
    Args:
        contexts: Dictionary of ContextWindow objects
        
    Returns:
        Dictionary with statistics
    """
    total_segments = len(contexts)
    segments_with_before = sum(1 for c in contexts.values() if c.before_text)
    segments_with_after = sum(1 for c in contexts.values() if c.after_text)
    
    avg_before_duration = (
        sum(c.before_duration for c in contexts.values()) / total_segments
        if total_segments > 0 else 0
    )
    
    avg_after_duration = (
        sum(c.after_duration for c in contexts.values()) / total_segments
        if total_segments > 0 else 0
    )
    
    avg_current_length = (
        sum(len(c.current_text) for c in contexts.values()) / total_segments
        if total_segments > 0 else 0
    )
    
    return {
        'total_segments': total_segments,
        'segments_with_before_context': segments_with_before,
        'segments_with_after_context': segments_with_after,
        'avg_before_duration_seconds': avg_before_duration,
        'avg_after_duration_seconds': avg_after_duration,
        'avg_current_text_length_chars': avg_current_length
    }

