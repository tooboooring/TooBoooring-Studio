"""
Unit test for context_builder module.

Tests that the context window logic correctly gathers preceding and following
segments within the specified time window.
"""

import sys
import io
import re
from pathlib import Path

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add temp_repo to Python path so we can import video_production_app
_current_file = Path(__file__).resolve()
_temp_repo = _current_file.parent.parent  # tests/ -> temp_repo/
if str(_temp_repo) not in sys.path:
    sys.path.insert(0, str(_temp_repo))

from video_production_app.ai_analysis.context_builder import build_context, ContextWindow
from video_production_app.ai_analysis.transcriber import TranscriptSegment
from video_production_app.config import AI_ANALYSIS_SETTINGS


def create_mock_transcripts() -> dict:
    """
    Create mock transcript segments covering 2 minutes (0-120 seconds).
    Each segment is 5 seconds long, with distinct text for easy identification.
    
    Returns:
        Dictionary mapping segment_id to TranscriptSegment objects
    """
    transcripts = {}
    
    # Create segments every 5 seconds from 0 to 120 seconds
    # Segment 0: 0-5s, Segment 1: 5-10s, ..., Segment 23: 115-120s
    for i in range(24):  # 24 segments * 5 seconds = 120 seconds
        start_time = i * 5.0
        end_time = (i + 1) * 5.0
        segment_id = f"segment_{i}"
        
        transcript = TranscriptSegment(
            segment_id=segment_id,
            start_time=start_time,
            end_time=end_time,
            text=f"This is segment {i} covering {start_time:.0f} to {end_time:.0f} seconds."
        )
        
        transcripts[segment_id] = transcript
    
    return transcripts


def create_mock_segments() -> list:
    """
    Create mock segment list (original format from silence detection).
    
    Returns:
        List of segment dictionaries
    """
    segments = []
    
    for i in range(24):
        segments.append({
            'start': i * 5.0,
            'end': (i + 1) * 5.0,
            'type': 'audible',
            'keep': True
        })
    
    return segments


def test_context_window():
    """Test the context window logic."""
    
    print("=" * 80)
    print("CONTEXT BUILDER UNIT TEST")
    print("=" * 80)
    print()
    
    # Create mock data
    transcripts = create_mock_transcripts()
    segments = create_mock_segments()
    
    # Get default context window from config
    context_window_seconds = AI_ANALYSIS_SETTINGS.get("context_window_seconds", 30.0)
    
    # Select target segment from the middle (segment 12 = 60-65 seconds)
    target_segment_id = "segment_12"
    target_segment = transcripts[target_segment_id]
    
    print(f"Test Configuration:")
    print(f"  Total segments: {len(transcripts)}")
    print(f"  Target segment: {target_segment_id}")
    print(f"  Target time range: {target_segment.start_time:.1f}s - {target_segment.end_time:.1f}s")
    print(f"  Context window: {context_window_seconds} seconds")
    print()
    
    # Build context for target segment
    try:
        context = build_context(
            transcripts=transcripts,
            target_segment_id=target_segment_id,
            segments=segments,
            context_window_seconds=context_window_seconds
        )
        
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        print()
        
        # Display target segment
        print(f"TARGET SEGMENT ({context.start_time:.1f}s - {context.end_time:.1f}s):")
        print(f"  {context.current_text}")
        print()
        
        # Display preceding context
        print(f"PRECEDING CONTEXT (from {context.before_duration:.1f}s before):")
        if context.before_text:
            print(f"  {context.before_text}")
            # Show which segments should be included
            expected_before_start = max(0, target_segment.start_time - context_window_seconds)
            print(f"  Expected segments: {expected_before_start:.1f}s to {target_segment.start_time:.1f}s")
        else:
            print("  (No preceding context)")
        print()
        
        # Display following context
        print(f"FOLLOWING CONTEXT (next {context.after_duration:.1f}s):")
        if context.after_text:
            print(f"  {context.after_text}")
            # Show which segments should be included
            expected_after_end = min(120, target_segment.end_time + context_window_seconds)
            print(f"  Expected segments: {target_segment.end_time:.1f}s to {expected_after_end:.1f}s")
        else:
            print("  (No following context)")
        print()
        
        # Verification
        print("=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        print()
        
        all_passed = True
        
        # Check 1: Target segment text is correct
        expected_target_text = f"This is segment 12 covering 60 to 65 seconds."
        if context.current_text == expected_target_text:
            print("✓ PASS: Target segment text is correct")
        else:
            print(f"✗ FAIL: Target segment text mismatch")
            print(f"  Expected: {expected_target_text}")
            print(f"  Got: {context.current_text}")
            all_passed = False
        
        # Check 2: Preceding context should include segments 5-11
        # Logic: time_gap = target_start - seg_end <= 30
        # For target at 60s: seg_end >= 30s
        # Segment 5: 25-30s (end=30, gap=30, included)
        # Segment 6-11: 30-60s (all included)
        expected_before_segments = [5, 6, 7, 8, 9, 10, 11]
        before_text_lower = context.before_text.lower()
        
        missing_before = []
        for seg_num in expected_before_segments:
            expected_text = f"segment {seg_num}"
            if expected_text not in before_text_lower:
                missing_before.append(seg_num)
        
        if not missing_before:
            print("✓ PASS: Preceding context includes expected segments (5-11)")
        else:
            print(f"✗ FAIL: Preceding context missing segments: {missing_before}")
            all_passed = False
        
        # Check 3: Preceding context should NOT include segments before 25s (segments 0-4)
        # Segment 4: 20-25s (end=25, gap=35, excluded)
        # Use word boundaries to avoid false matches (e.g., "segment 1" matching "segment 10")
        unexpected_before = []
        for seg_num in range(0, 5):
            # Use word boundary regex to match "segment X" but not "segment X0" or "segment X1"
            pattern = rf'\bsegment {seg_num}\b'
            if re.search(pattern, before_text_lower):
                unexpected_before.append(seg_num)
        
        if not unexpected_before:
            print("✓ PASS: Preceding context correctly excludes segments before 25s")
        else:
            print(f"✗ FAIL: Preceding context incorrectly includes segments: {unexpected_before}")
            all_passed = False
        
        # Check 4: Following context should include segments 13-19
        # Logic: time_gap = seg_start - target_end <= 30
        # For target ending at 65s: seg_start <= 95s
        # Segment 13-18: 65-95s (all included)
        # Segment 19: 95-100s (start=95, gap=30, included)
        expected_after_segments = [13, 14, 15, 16, 17, 18, 19]
        after_text_lower = context.after_text.lower()
        
        missing_after = []
        for seg_num in expected_after_segments:
            expected_text = f"segment {seg_num}"
            if expected_text not in after_text_lower:
                missing_after.append(seg_num)
        
        if not missing_after:
            print("✓ PASS: Following context includes expected segments (13-19)")
        else:
            print(f"✗ FAIL: Following context missing segments: {missing_after}")
            all_passed = False
        
        # Check 5: Following context should NOT include segments after 100s (segments 20-23)
        # Segment 20: 100-105s (start=100, gap=35, excluded)
        unexpected_after = []
        for seg_num in range(20, 24):
            unexpected_text = f"segment {seg_num}"
            if unexpected_text in after_text_lower:
                unexpected_after.append(seg_num)
        
        if not unexpected_after:
            print("✓ PASS: Following context correctly excludes segments after 100s")
        else:
            print(f"✗ FAIL: Following context incorrectly includes segments: {unexpected_after}")
            all_passed = False
        
        # Check 6: Duration calculations
        if 25.0 <= context.before_duration <= 35.0:  # Allow some tolerance
            print(f"✓ PASS: Before duration is reasonable ({context.before_duration:.1f}s)")
        else:
            print(f"✗ FAIL: Before duration seems incorrect ({context.before_duration:.1f}s)")
            all_passed = False
        
        if 25.0 <= context.after_duration <= 35.0:  # Allow some tolerance
            print(f"✓ PASS: After duration is reasonable ({context.after_duration:.1f}s)")
        else:
            print(f"✗ FAIL: After duration seems incorrect ({context.after_duration:.1f}s)")
            all_passed = False
        
        print()
        print("=" * 80)
        if all_passed:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        print("=" * 80)
        
        return all_passed
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_context_window()
    exit(0 if success else 1)

