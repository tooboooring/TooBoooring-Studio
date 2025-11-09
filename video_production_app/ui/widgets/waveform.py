"""
Audio waveform generation and visualization for Video Production App.

This module handles the extraction and processing of audio waveforms from video files
for visualization in the interactive timeline. It uses FFmpeg to extract audio and
librosa for audio analysis and waveform generation.

Key features:
- Multi-track audio waveform extraction
- Waveform downsampling for display
- Temporary file management
- Error handling and cleanup

The WaveformGenerator class provides static methods for extracting waveforms
from video files and processing them for display in the UI.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable

# Check for optional audio analysis packages
try:
    import librosa
    import numpy as np
    AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    AUDIO_ANALYSIS_AVAILABLE = False
    print("[WARNING] librosa/soundfile not installed. Waveform visualization disabled.")


class WaveformGenerator:
    """
    Generates audio waveform visualization from video files.
    
    This class provides static methods for extracting audio waveforms from video files
    and processing them for display. It handles multiple audio tracks separately and
    provides downsampling for efficient display.
    
    The class uses FFmpeg to extract audio tracks and librosa for audio analysis.
    If librosa is not available, waveform generation is disabled with appropriate
    error messages.
    
    Example usage:
        # Extract waveforms for all tracks
        waveforms = WaveformGenerator.extract_audio_waveforms_all_tracks(
            "video.mp4", "", audio_tracks, print
        )
        
        # Downsample for display
        if waveforms:
            waveform = waveforms[0]["waveform"]
            display_waveform = WaveformGenerator.downsample_waveform(waveform, 800)
    """
    
    @staticmethod
    def extract_audio_waveforms_all_tracks(video_path: str, ffmpeg_path: str, 
                                         audio_tracks: List[Dict[str, Any]],
                                         status_callback: Optional[Callable[[str], None]] = None) -> Dict[int, Dict[str, Any]]:
        """
        Extract waveforms for ALL audio tracks separately.
        
        This method processes each audio track in a video file individually,
        extracting the audio waveform data for visualization. It handles
        multiple tracks and provides detailed status updates.
        
        Args:
            video_path: Path to the video file
            ffmpeg_path: Path to FFmpeg executable (empty string uses system PATH)
            audio_tracks: List of audio track information dictionaries
            status_callback: Optional function to call with status messages
            
        Returns:
            Dictionary mapping track indices to waveform data:
            {
                track_index: {
                    "waveform": numpy array of audio samples,
                    "track_info": original track information
                }
            }
            
        Example:
            audio_tracks = [{"audio_index": 0, "stream_index": 1, "name": "Track 1"}]
            waveforms = WaveformGenerator.extract_audio_waveforms_all_tracks(
                "video.mp4", "", audio_tracks, print
            )
            # Returns: {0: {"waveform": array([...]), "track_info": {...}}}
        """
        # Check if audio analysis is available
        if not AUDIO_ANALYSIS_AVAILABLE:
            if status_callback:
                status_callback("⚠️ librosa not installed. Waveform unavailable.\n")
            return {}
        
        waveforms = {}
        
        try:
            # Process each audio track
            for track in audio_tracks:
                track_index = track["audio_index"]
                stream_index = track["stream_index"]
                
                if status_callback:
                    status_callback(f"📊 Extracting waveform for Track {track_index + 1}...\n")
                
                # Create temporary file for this track
                temp_audio = Path(video_path).parent / f"_temp_audio_track{track_index}.wav"
                ffmpeg_exe = ffmpeg_path or "ffmpeg"
                
                # Build FFmpeg command to extract specific audio track
                cmd = [
                    str(ffmpeg_exe), 
                    "-y",  # Overwrite output file
                    "-i", str(video_path),  # Input video file
                    "-map", f"0:{stream_index}",  # Map specific audio stream
                    "-acodec", "pcm_s16le",  # Convert to 16-bit PCM
                    "-ar", "22050",  # Sample rate: 22.05 kHz
                    "-ac", "1",  # Mono audio
                    str(temp_audio)  # Output file
                ]
                
                # Set up Windows-specific startup info
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                # Run FFmpeg to extract audio
                subprocess.run(cmd, check=True, capture_output=True, startupinfo=startupinfo)
                
                # Load audio with librosa for analysis
                y, sr = librosa.load(str(temp_audio), sr=22050, mono=True)
                
                # Store waveform data
                waveforms[track_index] = {
                    "waveform": y,  # Audio samples as numpy array
                    "track_info": track  # Original track information
                }
                
                # Clean up temporary file
                if temp_audio.exists():
                    temp_audio.unlink()
            
            if status_callback:
                status_callback(f"✅ Extracted {len(waveforms)} waveforms!\n")
            
            return waveforms
            
        except Exception as e:
            if status_callback:
                status_callback(f"⚠️ Waveform extraction failed: {e}\n")
            
            # Clean up any temporary files that might have been created
            for i in range(10):  # Check for potential temp files
                temp_audio = Path(video_path).parent / f"_temp_audio_track{i}.wav"
                if temp_audio.exists():
                    temp_audio.unlink()
            
            return waveforms
    
    @staticmethod
    def extract_audio_waveform(video_path: str, ffmpeg_path: str, 
                              status_callback: Optional[Callable[[str], None]] = None) -> Optional[np.ndarray]:
        """
        Extract mixed audio waveform from video (legacy method for single track).
        
        This method extracts audio from a video file and returns the waveform
        as a numpy array. It's a simpler version for cases where you only need
        one waveform (mixed from all audio tracks).
        
        Args:
            video_path: Path to the video file
            ffmpeg_path: Path to FFmpeg executable (empty string uses system PATH)
            status_callback: Optional function to call with status messages
            
        Returns:
            Numpy array of audio samples, or None if extraction failed
            
        Example:
            waveform = WaveformGenerator.extract_audio_waveform("video.mp4", "", print)
            if waveform is not None:
                print(f"Extracted {len(waveform)} audio samples")
        """
        # Check if audio analysis is available
        if not AUDIO_ANALYSIS_AVAILABLE:
            if status_callback:
                status_callback("⚠️ librosa not installed. Waveform unavailable.\n")
            return None
        
        try:
            if status_callback:
                status_callback("📊 Extracting audio waveform...\n")
            
            # Create temporary file for audio extraction
            temp_audio = Path(video_path).parent / "_temp_audio.wav"
            ffmpeg_exe = ffmpeg_path or "ffmpeg"
            
            # Build FFmpeg command to extract audio
            cmd = [
                str(ffmpeg_exe), 
                "-y",  # Overwrite output file
                "-i", str(video_path),  # Input video file
                "-vn",  # No video (audio only)
                "-acodec", "pcm_s16le",  # Convert to 16-bit PCM
                "-ar", "22050",  # Sample rate: 22.05 kHz
                "-ac", "1",  # Mono audio
                str(temp_audio)  # Output file
            ]
            
            # Set up Windows-specific startup info
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Run FFmpeg to extract audio
            subprocess.run(cmd, check=True, capture_output=True, startupinfo=startupinfo)
            
            # Load audio with librosa
            y, sr = librosa.load(str(temp_audio), sr=22050, mono=True)
            
            # Clean up temporary file
            if temp_audio.exists():
                temp_audio.unlink()
            
            if status_callback:
                status_callback("✅ Waveform extracted!\n")
            
            return y
            
        except Exception as e:
            if status_callback:
                status_callback(f"⚠️ Waveform extraction failed: {e}\n")
            
            # Clean up temporary file
            temp_audio = Path(video_path).parent / "_temp_audio.wav"
            if temp_audio.exists():
                temp_audio.unlink()
            
            return None
    
    @staticmethod
    def downsample_waveform(waveform: np.ndarray, target_width: int) -> np.ndarray:
        """
        Downsample waveform to fit display width efficiently.
        
        This method reduces the number of samples in a waveform to match
        the display width while preserving the important visual characteristics.
        It uses maximum value sampling to ensure peaks are visible.
        
        Args:
            waveform: Numpy array of audio samples
            target_width: Desired number of samples for display
            
        Returns:
            Downsampled waveform array
            
        Example:
            # Original waveform has 100,000 samples
            waveform = np.random.randn(100000)
            
            # Downsample to 800 samples for display
            display_waveform = WaveformGenerator.downsample_waveform(waveform, 800)
            # Result: array with 800 samples showing waveform peaks
        """
        # If waveform is already small enough, return as-is
        if len(waveform) <= target_width:
            return waveform
        
        # Calculate how many samples to group together
        samples_per_pixel = len(waveform) // target_width
        
        # Trim waveform to exact multiple of samples_per_pixel
        trimmed_length = target_width * samples_per_pixel
        waveform_trimmed = waveform[:trimmed_length]
        
        # Reshape waveform into groups
        # Each group contains samples_per_pixel samples
        waveform_reshaped = waveform_trimmed.reshape(target_width, samples_per_pixel)
        
        # Take maximum absolute value from each group
        # This preserves peaks and important visual features
        downsampled = np.max(np.abs(waveform_reshaped), axis=1)
        
        return downsampled
    
    @staticmethod
    def normalize_waveform(waveform: np.ndarray, target_range: float = 1.0) -> np.ndarray:
        """
        Normalize waveform to a specific range for consistent display.
        
        This method scales a waveform so its maximum value matches the
        target range, ensuring consistent visual appearance across
        different audio levels.
        
        Args:
            waveform: Numpy array of audio samples
            target_range: Maximum value for normalized waveform (default: 1.0)
            
        Returns:
            Normalized waveform array
            
        Example:
            # Waveform with values between -0.5 and 0.5
            waveform = np.array([-0.3, 0.1, 0.5, -0.2])
            
            # Normalize to range -1.0 to 1.0
            normalized = WaveformGenerator.normalize_waveform(waveform, 1.0)
            # Result: array scaled so max absolute value is 1.0
        """
        if len(waveform) == 0:
            return waveform
        
        # Find maximum absolute value
        max_value = np.max(np.abs(waveform))
        
        # Avoid division by zero
        if max_value == 0:
            return waveform
        
        # Scale waveform to target range
        normalized = waveform * (target_range / max_value)
        
        return normalized
    
    @staticmethod
    def get_waveform_statistics(waveform: np.ndarray) -> Dict[str, float]:
        """
        Calculate statistics for a waveform.
        
        This method provides useful statistics about a waveform that can
        be used for analysis or display purposes.
        
        Args:
            waveform: Numpy array of audio samples
            
        Returns:
            Dictionary containing waveform statistics:
            - max_amplitude: Maximum absolute value
            - rms: Root mean square (average energy)
            - peak_to_peak: Difference between max and min values
            - zero_crossings: Number of times waveform crosses zero
            
        Example:
            waveform = np.array([-0.5, 0.3, -0.1, 0.8, -0.2])
            stats = WaveformGenerator.get_waveform_statistics(waveform)
            # Returns: {"max_amplitude": 0.8, "rms": 0.45, ...}
        """
        if len(waveform) == 0:
            return {
                "max_amplitude": 0.0,
                "rms": 0.0,
                "peak_to_peak": 0.0,
                "zero_crossings": 0
            }
        
        # Calculate statistics
        max_amplitude = np.max(np.abs(waveform))
        rms = np.sqrt(np.mean(waveform ** 2))
        peak_to_peak = np.max(waveform) - np.min(waveform)
        
        # Count zero crossings
        zero_crossings = np.sum(np.diff(np.sign(waveform)) != 0)
        
        return {
            "max_amplitude": float(max_amplitude),
            "rms": float(rms),
            "peak_to_peak": float(peak_to_peak),
            "zero_crossings": int(zero_crossings)
        }
