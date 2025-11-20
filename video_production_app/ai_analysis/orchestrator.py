"""
Orchestrator for AI content analysis pipeline.

Coordinates the full workflow: transcription → context building → AI analysis → results.
"""

import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from .transcriber import transcribe_segments, check_whisper_available
from .context_builder import build_all_contexts, get_segment_statistics
from .ai_analyzer import analyze_segments_batch, Decision, export_decisions_to_json, validate_api_connection


# Global cache for transcriptions (in-memory, persists across analysis runs in same session)
_TRANSCRIPT_CACHE: Dict[str, Dict[str, Any]] = {}


def _generate_cache_key(video_path: str, segments: List[Dict[str, Any]], whisper_model: str) -> str:
    """
    Generate a unique cache key for transcription results.
    
    Cache key is based on:
    - Video file path
    - Segment timestamps (only audible segments)
    - Whisper model size
    
    Returns:
        MD5 hash string to use as cache key
    """
    # Extract audible segments only
    audible_segments = [seg for seg in segments if seg.get('type') == 'audible']
    
    # Create a string representation of segments (start:end pairs)
    segments_str = "|".join([f"{seg['start']:.2f}:{seg['end']:.2f}" for seg in audible_segments])
    
    # Combine video path, segments, and model
    cache_input = f"{video_path}|{segments_str}|{whisper_model}"
    
    # Generate MD5 hash
    return hashlib.md5(cache_input.encode('utf-8')).hexdigest()


def clear_transcript_cache() -> None:
    """Clear the global transcript cache."""
    global _TRANSCRIPT_CACHE
    _TRANSCRIPT_CACHE.clear()


@dataclass
class AnalysisResults:
    """Results from the complete AI analysis pipeline."""
    segments_analyzed: int
    keep_count: int
    flag_count: int
    uncertain_count: int
    avg_confidence: float
    processing_time: float
    decisions: Dict[str, Any]  # segment_id -> decision data
    transcripts: Dict[str, Any]  # segment_id -> transcript
    errors: List[str]


def analyze_content(
    video_path: str,
    segments: List[Dict[str, Any]],
    api_key: str,
    ffmpeg_path: str = "",
    whisper_model: str = "base",
    together_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    prompt_template: Optional[str] = None,
    context_window_seconds: float = 30.0,
    status_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
    export_path: Optional[str] = None
) -> AnalysisResults:
    """
    Run the complete AI analysis pipeline on video segments.
    
    This is the main entry point for AI content analysis. It coordinates:
    1. Transcription of audible segments using Whisper (with caching)
    2. Context building (extracting before/after text)
    3. AI analysis using together.ai
    4. Aggregation of results
    
    Performance Optimization:
        Transcriptions are cached in memory. If you run analysis multiple times
        on the same video with the same segments and Whisper model, transcription
        will be skipped and cached results will be used. This saves significant
        time (typically 20-60 seconds per run).
        
        Cache is session-based (cleared when app restarts). Use clear_transcript_cache()
        to manually clear the cache if needed.
    
    Args:
        video_path: Path to the video file
        segments: List of segment dictionaries from silence detection
        api_key: together.ai API key
        ffmpeg_path: Path to FFmpeg executable
        whisper_model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        together_model: together.ai model ID
        prompt_template: Optional custom prompt template
        context_window_seconds: Context window size (seconds before/after)
        status_callback: Callback for status messages
        progress_callback: Callback for progress updates (stage, current, total)
        export_path: Optional path to export results JSON
        
    Returns:
        AnalysisResults object with complete analysis data
        
    Example:
        results = analyze_content(
            video_path="video.mp4",
            segments=detected_segments,
            api_key="your_api_key",
            status_callback=print
        )
        
        # Second run on same video - transcription skipped (uses cache)
        results2 = analyze_content(
            video_path="video.mp4",
            segments=detected_segments,
            api_key="your_api_key",
            status_callback=print
        )
    """
    start_time = time.time()
    errors = []
    
    def log(msg: str):
        if status_callback:
            status_callback(msg)
    
    def progress(stage: str, current: int, total: int):
        if progress_callback:
            progress_callback(stage, current, total)
    
    log("=" * 60 + "\n")
    log("🚀 Starting AI Content Analysis Pipeline\n")
    log("=" * 60 + "\n\n")
    
    # Validate prerequisites
    log("🔍 Checking prerequisites...\n")
    
    if not check_whisper_available():
        error_msg = "Whisper is not installed. Please install: pip install openai-whisper"
        log(f"❌ {error_msg}\n")
        errors.append(error_msg)
        return AnalysisResults(
            segments_analyzed=0,
            keep_count=0,
            flag_count=0,
            uncertain_count=0,
            avg_confidence=0.0,
            processing_time=time.time() - start_time,
            decisions={},
            transcripts={},
            errors=errors
        )
    
    if not api_key:
        error_msg = "together.ai API key is required"
        log(f"❌ {error_msg}\n")
        errors.append(error_msg)
        return AnalysisResults(
            segments_analyzed=0,
            keep_count=0,
            flag_count=0,
            uncertain_count=0,
            avg_confidence=0.0,
            processing_time=time.time() - start_time,
            decisions={},
            transcripts={},
            errors=errors
        )
    
    # Validate API connection BEFORE transcription (fail fast)
    log(f"   ✓ Whisper model: {whisper_model}\n")
    log(f"   ✓ Together.ai model: {together_model}\n")
    log(f"   ✓ API key: {'*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '***'}\n")
    log(f"\n🔌 Validating API connection...\n")
    
    try:
        validate_api_connection(api_key=api_key, model=together_model, timeout=60)
        log(f"   ✅ API connection validated successfully\n")
    except ValueError as e:
        # Authentication error
        error_msg = f"API Authentication Failed: {str(e)}"
        log(f"   ❌ {error_msg}\n")
        errors.append(error_msg)
        return AnalysisResults(
            segments_analyzed=0,
            keep_count=0,
            flag_count=0,
            uncertain_count=0,
            avg_confidence=0.0,
            processing_time=time.time() - start_time,
            decisions={},
            transcripts={},
            errors=errors
        )
    except ConnectionError as e:
        # Network error
        error_msg = f"API Connection Failed: {str(e)}"
        log(f"   ❌ {error_msg}\n")
        errors.append(error_msg)
        return AnalysisResults(
            segments_analyzed=0,
            keep_count=0,
            flag_count=0,
            uncertain_count=0,
            avg_confidence=0.0,
            processing_time=time.time() - start_time,
            decisions={},
            transcripts={},
            errors=errors
        )
    except TimeoutError as e:
        # Timeout error (60 seconds)
        error_msg = f"API Validation Timeout: {str(e)}"
        log(f"   ❌ {error_msg}\n")
        errors.append(error_msg)
        return AnalysisResults(
            segments_analyzed=0,
            keep_count=0,
            flag_count=0,
            uncertain_count=0,
            avg_confidence=0.0,
            processing_time=time.time() - start_time,
            decisions={},
            transcripts={},
            errors=errors
        )
    except Exception as e:
        # Unexpected error during validation
        error_msg = f"API Validation Failed: {str(e)}"
        log(f"   ❌ {error_msg}\n")
        errors.append(error_msg)
        return AnalysisResults(
            segments_analyzed=0,
            keep_count=0,
            flag_count=0,
            uncertain_count=0,
            avg_confidence=0.0,
            processing_time=time.time() - start_time,
            decisions={},
            transcripts={},
            errors=errors
        )
    
    log("✅ Prerequisites check passed\n\n")
    
    # Step 1: Transcription (with caching)
    log("-" * 60 + "\n")
    log("STEP 1: TRANSCRIPTION\n")
    log("-" * 60 + "\n")
    
    # Check cache first
    cache_key = _generate_cache_key(video_path, segments, whisper_model)
    
    if cache_key in _TRANSCRIPT_CACHE:
        # Use cached transcripts
        transcripts = _TRANSCRIPT_CACHE[cache_key]
        log(f"💾 Using cached transcriptions ({len(transcripts)} segments)\n")
        log(f"   ⚡ Skipping transcription - already processed\n")
        log(f"\n✅ Transcription complete (from cache): {len(transcripts)} segments\n\n")
    else:
        # Transcribe and cache results
        try:
            transcripts = transcribe_segments(
                video_path=video_path,
                segments=segments,
                model_size=whisper_model,
                ffmpeg_path=ffmpeg_path,
                status_callback=log,
                progress_callback=lambda curr, total: progress("transcription", curr, total)
            )
            
            # Store in cache for future runs
            _TRANSCRIPT_CACHE[cache_key] = transcripts
            log(f"💾 Cached transcriptions for future use\n")
            
            log(f"\n✅ Transcription complete: {len(transcripts)} segments transcribed\n\n")
        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            log(f"❌ {error_msg}\n")
            errors.append(error_msg)
            return AnalysisResults(
                segments_analyzed=0,
                keep_count=0,
                flag_count=0,
                uncertain_count=0,
                avg_confidence=0.0,
                processing_time=time.time() - start_time,
                decisions={},
                transcripts={},
                errors=errors
            )
    
    # Step 2: Context Building
    log("-" * 60 + "\n")
    log("STEP 2: CONTEXT BUILDING\n")
    log("-" * 60 + "\n")
    
    try:
        contexts = build_all_contexts(
            transcripts=transcripts,
            segments=segments,
            context_window_seconds=context_window_seconds
        )
        
        stats = get_segment_statistics(contexts)
        log(f"📊 Context Statistics:\n")
        log(f"   Total segments: {stats['total_segments']}\n")
        log(f"   Segments with before context: {stats['segments_with_before_context']}\n")
        log(f"   Segments with after context: {stats['segments_with_after_context']}\n")
        log(f"   Avg before duration: {stats['avg_before_duration_seconds']:.1f}s\n")
        log(f"   Avg after duration: {stats['avg_after_duration_seconds']:.1f}s\n")
        log(f"\n✅ Context building complete\n\n")
    except Exception as e:
        error_msg = f"Context building failed: {str(e)}"
        log(f"❌ {error_msg}\n")
        errors.append(error_msg)
        # Continue without context
        contexts = {}
    
    # Step 3: AI Analysis
    log("-" * 60 + "\n")
    log("STEP 3: AI ANALYSIS\n")
    log("-" * 60 + "\n")
    log(f"Model: {together_model}\n")
    log(f"Segments to analyze: {len(transcripts)}\n\n")
    
    # Prepare segments with context for batch analysis
    segments_with_context = {}
    for seg_id, transcript in transcripts.items():
        context = contexts.get(seg_id, None)
        segments_with_context[seg_id] = (transcript.text, context)
    
    try:
        # Import settings from config
        from ..config import AI_ANALYSIS_SETTINGS
        api_delay = AI_ANALYSIS_SETTINGS.get("api_delay_seconds", 0.5)
        temperature = AI_ANALYSIS_SETTINGS.get("temperature", 0.7)
        max_tokens = AI_ANALYSIS_SETTINGS.get("max_tokens", 500)
        
        # DeepSeek R1 needs much higher max_tokens due to verbose <think> reasoning
        # Note: Default max_tokens is now 8000 in config, which should be sufficient
        # But we can still override if needed for even more verbose models
        if "deepseek" in together_model.lower():
            # Use config value (8000) which is already high enough
            log(f"   🧠 DeepSeek model detected - using max_tokens={max_tokens} for verbose reasoning\n")
        
        decisions = analyze_segments_batch(
            segments_with_context=segments_with_context,
            api_key=api_key,
            model=together_model,
            prompt_template=prompt_template,
            status_callback=log,
            progress_callback=lambda curr, total: progress("analysis", curr, total),
            delay_between_requests=api_delay,  # Rate limiting (from config)
            temperature=temperature,  # LLM temperature (from config)
            max_tokens=max_tokens  # Max response tokens (from config)
        )
        
        log(f"\n✅ AI analysis complete: {len(decisions)} segments analyzed\n\n")
    except Exception as e:
        error_msg = f"AI analysis failed: {str(e)}"
        log(f"❌ {error_msg}\n")
        errors.append(error_msg)
        return AnalysisResults(
            segments_analyzed=len(transcripts),
            keep_count=0,
            flag_count=0,
            uncertain_count=0,
            avg_confidence=0.0,
            processing_time=time.time() - start_time,
            decisions={},
            transcripts={seg_id: t.__dict__ for seg_id, t in transcripts.items()},
            errors=errors
        )
    
    # Step 4: Aggregate Results
    log("-" * 60 + "\n")
    log("STEP 4: RESULTS AGGREGATION\n")
    log("-" * 60 + "\n")
    
    keep_count = sum(1 for d in decisions.values() if d.decision == Decision.KEEP)
    flag_count = sum(1 for d in decisions.values() if d.decision == Decision.FLAG)
    uncertain_count = sum(1 for d in decisions.values() if d.decision == Decision.UNCERTAIN)
    
    avg_confidence = (
        sum(d.confidence for d in decisions.values()) / len(decisions)
        if decisions else 0.0
    )
    
    total_time = time.time() - start_time
    
    log(f"📊 Analysis Summary:\n")
    log(f"   Total segments analyzed: {len(decisions)}\n")
    log(f"   ✅ KEEP: {keep_count} ({keep_count/len(decisions)*100:.1f}%)\n")
    log(f"   ⚠️  FLAG: {flag_count} ({flag_count/len(decisions)*100:.1f}%)\n")
    log(f"   ❓ UNCERTAIN: {uncertain_count} ({uncertain_count/len(decisions)*100:.1f}%)\n")
    log(f"   Average confidence: {avg_confidence:.2f}\n")
    log(f"   Total processing time: {total_time:.1f}s\n")
    
    # Convert decisions to serializable format
    decisions_dict = {}
    for seg_id, decision in decisions.items():
        decisions_dict[seg_id] = {
            'decision': decision.decision.value,
            'confidence': decision.confidence,
            'reasoning': decision.reasoning,
            'model': decision.model,
            'processing_time': decision.processing_time
        }
    
    # Export to JSON if requested
    if export_path:
        try:
            export_decisions_to_json(decisions, export_path)
            log(f"\n💾 Results exported to: {export_path}\n")
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            log(f"⚠️  {error_msg}\n")
            errors.append(error_msg)
    
    log("\n" + "=" * 60 + "\n")
    log("✅ AI CONTENT ANALYSIS COMPLETE\n")
    log("=" * 60 + "\n")
    
    return AnalysisResults(
        segments_analyzed=len(decisions),
        keep_count=keep_count,
        flag_count=flag_count,
        uncertain_count=uncertain_count,
        avg_confidence=avg_confidence,
        processing_time=total_time,
        decisions=decisions_dict,
        transcripts={seg_id: t.__dict__ for seg_id, t in transcripts.items()},
        errors=errors
    )


def apply_decisions_to_segments(
    segments: List[Dict[str, Any]],
    decisions: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Apply AI decisions to the segment list.
    
    Updates the segment colors based on AI analysis:
    - KEEP decisions → keep=True, ai_decision='keep' (Green)
    - FLAG decisions → keep=False, ai_decision='flag' (Orange/Red)
    - UNCERTAIN → keep=False, ai_decision='uncertain' (Orange/Red - requires manual review)
    
    Note: UNCERTAIN segments default to flagged (keep=False) to ensure they are
    manually reviewed before inclusion. This is a "safety first" approach.
    
    Args:
        segments: Original list of segments
        decisions: Dictionary of decisions from analyze_content
        
    Returns:
        Updated segments list with AI decisions applied
    """
    # Create a mapping of segment times to decisions
    audible_segments = [seg for seg in segments if seg.get('type') == 'audible']
    
    # Create a counter for audible segment indexing
    audible_counter = 0
    
    # Apply decisions to segments
    updated_segments = []
    for seg_idx, segment in enumerate(segments):
        new_segment = segment.copy()
        
        # Only apply to audible segments
        if segment.get('type') == 'audible':
            # Use counter to map to audible segment index
            seg_id = f"segment_{audible_counter}"
            audible_counter += 1
            
            if seg_id in decisions:
                decision_data = decisions[seg_id]
                decision = decision_data['decision']
                
                # Update segment based on decision
                if decision == 'KEEP':
                    new_segment['keep'] = True
                    new_segment['ai_decision'] = 'keep'
                    new_segment['ai_confidence'] = decision_data['confidence']
                    new_segment['ai_reasoning'] = decision_data['reasoning']
                elif decision == 'FLAG':
                    new_segment['keep'] = False
                    new_segment['ai_decision'] = 'flag'
                    new_segment['ai_confidence'] = decision_data['confidence']
                    new_segment['ai_reasoning'] = decision_data['reasoning']
                else:  # UNCERTAIN
                    # Uncertain -> Default to Flag (requires user review)
                    # Safety first: if AI isn't confident, flag for manual review
                    new_segment['keep'] = False
                    new_segment['ai_decision'] = 'uncertain'
                    new_segment['ai_confidence'] = decision_data['confidence']
                    new_segment['ai_reasoning'] = decision_data['reasoning']
        
        updated_segments.append(new_segment)
    
    return updated_segments

