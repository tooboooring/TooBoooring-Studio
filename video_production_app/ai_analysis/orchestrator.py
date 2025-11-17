"""
Orchestrator for AI content analysis pipeline.

Coordinates the full workflow: transcription → context building → AI analysis → results.
"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from .transcriber import transcribe_segments, check_whisper_available
from .context_builder import build_all_contexts, get_segment_statistics
from .ai_analyzer import analyze_segments_batch, Decision, export_decisions_to_json


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
    1. Transcription of audible segments using Whisper
    2. Context building (extracting before/after text)
    3. AI analysis using together.ai
    4. Aggregation of results
    
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
    
    log("✅ Prerequisites check passed\n\n")
    
    # Step 1: Transcription
    log("-" * 60 + "\n")
    log("STEP 1: TRANSCRIPTION\n")
    log("-" * 60 + "\n")
    
    try:
        transcripts = transcribe_segments(
            video_path=video_path,
            segments=segments,
            model_size=whisper_model,
            ffmpeg_path=ffmpeg_path,
            status_callback=log,
            progress_callback=lambda curr, total: progress("transcription", curr, total)
        )
        
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
        decisions = analyze_segments_batch(
            segments_with_context=segments_with_context,
            api_key=api_key,
            model=together_model,
            prompt_template=prompt_template,
            status_callback=log,
            progress_callback=lambda curr, total: progress("analysis", curr, total),
            delay_between_requests=0.5  # Rate limiting
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
    - KEEP decisions → keep=True, ai_decision='keep'
    - FLAG decisions → keep=False, ai_decision='flag'
    - UNCERTAIN → no change, ai_decision='uncertain'
    
    Args:
        segments: Original list of segments
        decisions: Dictionary of decisions from analyze_content
        
    Returns:
        Updated segments list with AI decisions applied
    """
    # Create a mapping of segment times to decisions
    audible_segments = [seg for seg in segments if seg.get('type') == 'audible']
    
    # Apply decisions to segments
    updated_segments = []
    for seg_idx, segment in enumerate(segments):
        new_segment = segment.copy()
        
        # Only apply to audible segments
        if segment.get('type') == 'audible':
            # Find the corresponding audible segment index
            audible_idx = [i for i, s in enumerate(audible_segments) if s == segment]
            if audible_idx:
                seg_id = f"segment_{audible_idx[0]}"
                
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
                        # Keep original 'keep' value, but mark as uncertain
                        new_segment['ai_decision'] = 'uncertain'
                        new_segment['ai_confidence'] = decision_data['confidence']
                        new_segment['ai_reasoning'] = decision_data['reasoning']
        
        updated_segments.append(new_segment)
    
    return updated_segments

