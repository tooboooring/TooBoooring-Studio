"""
Audio transcription module using local Whisper.

This module handles extracting audio from video segments and transcribing
them using OpenAI's Whisper model running locally (no API required).
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import json

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


@dataclass
class TranscriptSegment:
    """Represents a transcribed segment with timing information."""
    segment_id: str
    start_time: float
    end_time: float
    text: str
    words: Optional[List[Dict[str, Any]]] = None  # Word-level timestamps if available
    

def check_whisper_available() -> bool:
    """Check if Whisper is installed and available."""
    return WHISPER_AVAILABLE


def transcribe_segments(
    video_path: str,
    segments: List[Dict[str, Any]],
    model_size: str = "base",
    ffmpeg_path: str = "",
    status_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Dict[str, TranscriptSegment]:
    """
    Transcribe audio from specific video segments using Whisper.
    
    Args:
        video_path: Path to the source video file
        segments: List of segment dictionaries with 'start', 'end', 'type', 'keep' keys
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        ffmpeg_path: Path to FFmpeg executable (empty string uses system PATH)
        status_callback: Optional callback for status messages
        progress_callback: Optional callback for progress (current, total)
        
    Returns:
        Dictionary mapping segment_id to TranscriptSegment objects
        
    Example:
        segments = [
            {'start': 0.0, 'end': 10.5, 'type': 'audible', 'keep': True},
            {'start': 15.2, 'end': 25.8, 'type': 'audible', 'keep': True}
        ]
        transcripts = transcribe_segments("video.mp4", segments)
    """
    if not WHISPER_AVAILABLE:
        raise ImportError("Whisper is not installed. Install with: pip install openai-whisper")
    
    def log(msg: str):
        if status_callback:
            status_callback(msg)
    
    log("🎤 Starting transcription with Whisper...\n")
    log(f"   Model: {model_size}\n")
    
    # Load Whisper model
    log(f"📥 Loading Whisper model '{model_size}'...\n")
    try:
        model = whisper.load_model(model_size)
        log("✅ Model loaded successfully\n")
    except Exception as e:
        log(f"❌ Failed to load Whisper model: {e}\n")
        raise
    
    # Filter to only audible segments
    audible_segments = [seg for seg in segments if seg.get('type') == 'audible']
    total_segments = len(audible_segments)
    
    log(f"🔍 Found {total_segments} audible segments to transcribe\n")
    
    transcripts = {}
    ffmpeg_executable = ffmpeg_path or "ffmpeg"
    
    # Create temp directory for audio extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        for idx, segment in enumerate(audible_segments):
            segment_id = f"segment_{idx}"
            start_time = segment['start']
            end_time = segment['end']
            duration = end_time - start_time
            
            log(f"📝 [{idx + 1}/{total_segments}] Transcribing segment {start_time:.1f}s - {end_time:.1f}s ({duration:.1f}s)...\n")
            
            if progress_callback:
                progress_callback(idx + 1, total_segments)
            
            # Extract audio segment to temporary file
            temp_audio_file = Path(temp_dir) / f"{segment_id}.wav"
            
            try:
                # Use FFmpeg to extract audio segment
                extract_cmd = [
                    str(ffmpeg_executable),
                    "-y",  # Overwrite output
                    "-ss", str(start_time),  # Start time
                    "-i", str(video_path),  # Input video
                    "-t", str(duration),  # Duration
                    "-vn",  # No video
                    "-acodec", "pcm_s16le",  # PCM audio
                    "-ar", "16000",  # 16kHz sample rate (Whisper default)
                    "-ac", "1",  # Mono
                    str(temp_audio_file)
                ]
                
                # Windows: hide console window
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                result = subprocess.run(
                    extract_cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    startupinfo=startupinfo
                )
                
                # Transcribe the extracted audio
                transcription_result = model.transcribe(
                    str(temp_audio_file),
                    language="en",  # Assuming English; could be made configurable
                    word_timestamps=True  # Get word-level timestamps
                )
                
                # Extract text
                transcript_text = transcription_result['text'].strip()
                
                # Extract word-level timestamps if available
                words = []
                if 'segments' in transcription_result:
                    for seg in transcription_result['segments']:
                        if 'words' in seg:
                            for word in seg['words']:
                                words.append({
                                    'word': word.get('word', ''),
                                    'start': start_time + word.get('start', 0),
                                    'end': start_time + word.get('end', 0)
                                })
                
                # Create transcript object
                transcript = TranscriptSegment(
                    segment_id=segment_id,
                    start_time=start_time,
                    end_time=end_time,
                    text=transcript_text,
                    words=words if words else None
                )
                
                transcripts[segment_id] = transcript
                
                log(f"   ✓ '{transcript_text[:60]}{'...' if len(transcript_text) > 60 else ''}'\n")
                
            except subprocess.CalledProcessError as e:
                log(f"   ⚠️ Failed to extract audio for segment: {e}\n")
                # Add empty transcript for failed segment
                transcripts[segment_id] = TranscriptSegment(
                    segment_id=segment_id,
                    start_time=start_time,
                    end_time=end_time,
                    text="[Transcription failed]"
                )
            except Exception as e:
                log(f"   ⚠️ Transcription error: {e}\n")
                transcripts[segment_id] = TranscriptSegment(
                    segment_id=segment_id,
                    start_time=start_time,
                    end_time=end_time,
                    text="[Transcription error]"
                )
    
    log(f"✅ Transcription complete: {len(transcripts)} segments processed\n")
    return transcripts


def transcribe_full_video(
    video_path: str,
    model_size: str = "base",
    status_callback: Optional[Callable[[str], None]] = None
) -> List[Dict[str, Any]]:
    """
    Transcribe the entire video (for getting full context).
    
    This is useful when you need the complete transcript to build context
    windows around specific segments.
    
    Args:
        video_path: Path to the video file
        model_size: Whisper model size
        status_callback: Optional callback for status messages
        
    Returns:
        List of transcript segments with timing information
    """
    if not WHISPER_AVAILABLE:
        raise ImportError("Whisper is not installed. Install with: pip install openai-whisper")
    
    def log(msg: str):
        if status_callback:
            status_callback(msg)
    
    log("🎤 Transcribing full video...\n")
    log(f"   Model: {model_size}\n")
    
    # Load Whisper model
    try:
        model = whisper.load_model(model_size)
    except Exception as e:
        log(f"❌ Failed to load Whisper model: {e}\n")
        raise
    
    # Transcribe the video directly (Whisper can handle video files)
    try:
        result = model.transcribe(
            video_path,
            language="en",
            word_timestamps=True
        )
        
        # Convert to list format
        segments = []
        for seg in result.get('segments', []):
            segments.append({
                'start': seg.get('start', 0),
                'end': seg.get('end', 0),
                'text': seg.get('text', '').strip(),
                'words': seg.get('words', [])
            })
        
        log(f"✅ Full transcription complete: {len(segments)} segments\n")
        return segments
        
    except Exception as e:
        log(f"❌ Transcription failed: {e}\n")
        raise


def to_srt_format(transcripts: Dict[str, TranscriptSegment]) -> str:
    """
    Convert transcripts to SRT subtitle format.
    
    Args:
        transcripts: Dictionary of TranscriptSegment objects
        
    Returns:
        SRT-formatted string
    """
    srt_entries = []
    
    for idx, (segment_id, transcript) in enumerate(sorted(transcripts.items()), start=1):
        # Format timestamps as SRT format (HH:MM:SS,mmm)
        start_srt = _format_srt_timestamp(transcript.start_time)
        end_srt = _format_srt_timestamp(transcript.end_time)
        
        # SRT entry format:
        # 1
        # 00:00:00,000 --> 00:00:05,000
        # Subtitle text
        entry = f"{idx}\n{start_srt} --> {end_srt}\n{transcript.text}\n"
        srt_entries.append(entry)
    
    return "\n".join(srt_entries)


def _format_srt_timestamp(seconds: float) -> str:
    """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

