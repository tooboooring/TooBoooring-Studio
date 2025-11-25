import webview
import os
import sys
import time
from tkinter import Tk, filedialog
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Handle imports for both direct execution and module execution
if __name__ == '__main__':
    # Add parent directory to path when running directly
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from video_production_app.core.ffmpeg_wrapper import get_video_duration, get_audio_tracks, get_available_encoders, analyze_audio_track_content
    from video_production_app.core.silence_detector import detect_silence, parse_segments
    from video_production_app.core.settings_manager import SettingsManager
    from video_production_app.core.video_processor import process_video_logic
    from video_production_app.utils.waveform import WaveformGenerator
    from video_production_app.config import ENCODER_OPTIONS, UI_SETTINGS
    from video_production_app.utils.logger import app_logger
    from video_production_app.utils.validators import validate_video_path, validate_track_index, validate_trim_values
    import numpy as np
else:
        # Use relative imports when run as a module
        from ..core.ffmpeg_wrapper import get_video_duration, get_audio_tracks, get_available_encoders, analyze_audio_track_content
        from ..core.silence_detector import detect_silence, parse_segments
        from ..core.settings_manager import SettingsManager
        from ..core.video_processor import process_video_logic
        from ..utils.waveform import WaveformGenerator
        from ..config import ENCODER_OPTIONS, UI_SETTINGS
        from ..utils.logger import app_logger
        from ..utils.validators import validate_video_path, validate_track_index, validate_trim_values
        import numpy as np

# This is the "bridge" for JS to call Python
class Api:
    def __init__(self):
        self.settings = SettingsManager() # Assumes default config file
        self.window = None # We'll set this from main
        self.console_log = [] # To store logs
        self.available_encoders = [] # Store available encoders
        self.logger = app_logger.getChild("Api")
        # Performance: Waveform cache
        self.waveform_cache = {}  # Cache waveforms: {file_path:width: waveform_data}
        self.multi_track_cache = {}  # Cache multi-track waveforms: {file_path:width: {track_index: data}}
        # Temporary files management
        self.temp_video_files = []  # Track temporary video files for cleanup
        self.logger.info("API initialized")
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Return a standardized error response."""
        self.logger.error(f"Error: {message}")
        return {"status": "error", "error": message}
    
    def _success_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Return a standardized success response."""
        return {"status": "success", **data}
    
    def say_hello(self, name: str) -> str:
        """Test function to verify API is working."""
        self.logger.debug(f"say_hello called with name: {name}")
        return f"Hello, {name}! Python says hi."
    
    def log_to_console(self, message: str):
        """Sends a log message to the web UI console."""
        # Use logger instead of print
        self.logger.info(message)
        self.console_log.append(message)
        if self.window:
            # Call a *JavaScript* function from Python
            # Escape quotes and newlines for JavaScript
            escaped_message = message.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
            try:
                self.window.evaluate_js(f'window.app.addLog("{escaped_message}");')
            except Exception as e:
                self.logger.error(f"Error sending log to console: {e}")
    
    def get_app_config(self) -> Dict[str, Any]:
        """Called by JS on load to get encoders and settings."""
        self.logger.info("Getting app configuration")
        
        # Check FFmpeg/FFprobe availability first
        def status_cb(msg: str):
            self.logger.info(msg.strip())
            # Also send to web console if window is available
            if self.window:
                try:
                    escaped_msg = msg.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                    self.window.evaluate_js(f'window.app.addLog("{escaped_msg}");')
                except Exception as e:
                    self.logger.error(f"Error sending status to console: {e}")
        
        # Check FFmpeg availability
        import shutil
        ffmpeg_found = shutil.which("ffmpeg") is not None
        if ffmpeg_found:
            status_cb("✅ Found FFmpeg locally.\n")
        else:
            status_cb("⚠️ FFmpeg not found in PATH.\n")
        
        # Check FFprobe availability
        ffprobe_found = shutil.which("ffprobe") is not None
        if ffprobe_found:
            status_cb("✅ Found FFprobe locally.\n")
        else:
            status_cb("⚠️ FFprobe not found in PATH.\n")
        
        encoders = ["CPU (x264)"] # Default
        try:
            self.logger.debug("Starting encoder detection")
            encoders = get_available_encoders("", status_cb)
            self.logger.info(f"Found {len(encoders)} encoder(s): {encoders}")
            status_cb(f"📊 Encoder detection complete. Found {len(encoders)} option(s).\n")
        except Exception as e:
            self.logger.error(f"Could not get encoders: {e}", exc_info=True)
            status_cb(f"❌ Error detecting encoders: {str(e)}\n")
        
        # Save encoders for use in export_video
        self.available_encoders = encoders
        
        # Convert settings to JSON-serializable format (convert Path objects to strings)
        settings_dict = {}
        for key, value in self.settings.settings.items():
            if isinstance(value, Path):
                settings_dict[key] = str(value)
            else:
                settings_dict[key] = value
        
        result = {
            "encoders": encoders,
            "settings": settings_dict,  # Use serialized settings
            "ui_settings": UI_SETTINGS  # Include UI configuration
        }
        self.logger.debug(f"Returning config with {len(encoders)} encoders")
        return result
    
    def get_ai_settings(self) -> Dict[str, Any]:
        """
        Get AI analysis settings (whisper model and API key).
        
        Returns:
            Dict with whisper_model and api_key
        """
        self.logger.debug("Getting AI settings")
        import os
        
        # Priority: 1. Saved settings 2. Environment variable 3. Default
        saved_api_key = self.settings.get("api_key", "")
        env_api_key = os.getenv("TOGETHER_API_KEY", "")
        
        # Use env variable if available, otherwise use saved setting
        api_key = env_api_key if env_api_key else saved_api_key
        whisper_model = self.settings.get("whisper_model", "base")
        
        return {
            "whisper_model": whisper_model,
            "api_key": api_key,
            "api_key_source": "environment" if env_api_key else ("saved" if saved_api_key else "none")
        }
    
    def save_ai_settings(self, whisper_model: str, api_key: str = "") -> Dict[str, str]:
        """
        Save AI analysis settings.
        
        Args:
            whisper_model: Whisper model to use (tiny/base/small/medium/large)
            api_key: together.ai API key (optional, can be empty if using .env)
            
        Returns:
            Success status dict
        """
        self.logger.info(f"Saving AI settings: whisper_model={whisper_model}, api_key={'***' if api_key else '(empty)'}")
        
        # Validate whisper model
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if whisper_model not in valid_models:
            self.logger.warning(f"Invalid whisper model: {whisper_model}, defaulting to 'base'")
            whisper_model = "base"
        
        # Save settings
        self.settings.set("whisper_model", whisper_model)
        
        # Only save API key if provided (don't overwrite with empty string if user is using .env)
        if api_key:
            self.settings.set("api_key", api_key)
        
        self.logger.debug("AI settings saved successfully")
        return {"status": "success", "message": "AI settings saved"}
    
    def load_video(self) -> Optional[Dict[str, Any]]:
        """
        Load a video file and return its information.
        
        Returns:
            Dict with video info on success, None if cancelled, error dict on failure
        """
        root = Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)

        file_path = filedialog.askopenfilename(
            title="Select a Video File",
            filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi"), ("All Files", "*.*")]
        )
        root.destroy()

        if not file_path:
            self.logger.info("User cancelled file selection")
            return None

        self.logger.info(f"Loading video: {file_path}")

        # Validate file path
        is_valid, error_msg = validate_video_path(file_path)
        if not is_valid:
            self.logger.error(f"Invalid video path: {error_msg}")
            return self._error_response(error_msg)

        # Use console logger
        status_callback = self.log_to_console

        try:
            # Get info from our core Python files
            duration = get_video_duration(Path(file_path), "", status_callback)
            if duration <= 0:
                return self._error_response("Could not determine video duration")
            
            audio_tracks = get_audio_tracks(Path(file_path), "", status_callback)
            if not audio_tracks:
                self.logger.warning("No audio tracks found in video")

            video_info = {
                "filePath": file_path,
                "fileName": Path(file_path).name,
                "duration": duration,
                "audioTracks": audio_tracks
            }

            self.logger.info(f"Successfully loaded video: {video_info['fileName']} ({duration:.2f}s, {len(audio_tracks)} tracks)")
            # Return video_info directly (not wrapped) for backward compatibility
            # JavaScript checkError() will handle it correctly
            return video_info

        except Exception as e:
            self.logger.error(f"Error loading video: {e}", exc_info=True)
            return self._error_response(f"Error loading video: {str(e)}")
    
    def handle_dropped_file(self, file_name: str, file_data_base64: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Handle a file dropped in the UI by saving it temporarily and loading it.
        
        In PyWebView, we can't directly get the file path from drag and drop.
        This method accepts file data as base64, saves it temporarily, then loads it.
        
        Args:
            file_name: Name of the dropped file
            file_data_base64: Base64 encoded file data
            
        Returns:
            Dict with video info on success, None if invalid, error dict on failure
        """
        if not file_name:
            return None
        
        if not file_data_base64:
            # Fallback: Try to find the file by name in common locations
            self.logger.info(f"Handling dropped file (searching by name): {file_name}")
            from pathlib import Path
            
            # Common locations to search
            search_paths = [
                Path.home() / "Downloads",
                Path.home() / "Desktop",
                Path.home() / "Documents",
                Path.home() / "Videos",
                Path.cwd(),
            ]
            
            file_path = None
            for search_path in search_paths:
                potential_path = search_path / file_name
                if potential_path.exists() and potential_path.is_file():
                    file_path = str(potential_path.resolve())
                    self.logger.info(f"Found file at: {file_path}")
                    return self.load_video_from_path(file_path)
            
            # If we can't find it, return an error
            return self._error_response(
                f"Could not locate file '{file_name}'. Please use the 'Load Video' button to select the file."
            )
        
        # We have file data - save it temporarily and load it
        self.logger.info(f"Handling dropped file (saving from base64): {file_name}")
        
        try:
            import base64
            import tempfile
            
            # Decode base64 data
            file_bytes = base64.b64decode(file_data_base64)
            
            # Create temporary file
            temp_dir = Path(tempfile.gettempdir()) / "video_production_app"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            import uuid
            temp_filename = f"{uuid.uuid4().hex}_{file_name}"
            temp_path = temp_dir / temp_filename
            
            # Write file
            with open(temp_path, 'wb') as f:
                f.write(file_bytes)
            
            self.logger.info(f"Saved dropped file to: {temp_path}")
            
            # Load the video from the temp path
            result = self.load_video_from_path(str(temp_path))
            
            # Note: We keep the temp file for now (cleanup happens later)
            return result
            
        except Exception as e:
            self.logger.error(f"Error handling dropped file: {e}", exc_info=True)
            return self._error_response(f"Error processing dropped file: {str(e)}")
    
    def load_video_from_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load a video file from a given file path (for drag and drop).
        
        Args:
            file_path: Path to the video file
            
        Returns:
            Dict with video info on success, None if invalid, error dict on failure
        """
        if not file_path:
            self.logger.warning("Empty file path provided")
            return None
        
        self.logger.info(f"Loading video from path: {file_path}")
        
        # Validate file path
        is_valid, error_msg = validate_video_path(file_path)
        if not is_valid:
            self.logger.error(f"Invalid video path: {error_msg}")
            return self._error_response(error_msg)
        
        # Use console logger
        status_callback = self.log_to_console
        
        try:
            # Get info from our core Python files
            duration = get_video_duration(Path(file_path), "", status_callback)
            if duration <= 0:
                return self._error_response("Could not determine video duration")
            
            audio_tracks = get_audio_tracks(Path(file_path), "", status_callback)
            if not audio_tracks:
                self.logger.warning("No audio tracks found in video")
            
            video_info = {
                "filePath": file_path,
                "fileName": Path(file_path).name,
                "duration": duration,
                "audioTracks": audio_tracks
            }
            
            self.logger.info(f"Successfully loaded video: {video_info['fileName']} ({duration:.2f}s, {len(audio_tracks)} tracks)")
            return video_info
        except Exception as e:
            self.logger.error(f"Error loading video: {e}", exc_info=True)
            return self._error_response(f"Error loading video: {str(e)}")
    
    def detect_silence(self, video_path: str, track_index: Union[int, str]) -> Dict[str, Any]:
        """
        Detect silence in a video's audio track.
        
        Args:
            video_path: Path to video file
            track_index: Index of audio track to analyze
            
        Returns:
            Dict with segments on success, error dict on failure
        """
        self.logger.info(f"Detecting silence for {video_path} on track {track_index}")

        # Validate video path
        is_valid, error_msg = validate_video_path(video_path)
        if not is_valid:
            return self._error_response(error_msg)

        # Validate track index
        try:
            # Get audio tracks to validate track_index
            status_callback = self.log_to_console
            audio_tracks = get_audio_tracks(Path(video_path), "", status_callback)
            max_tracks = len(audio_tracks) if audio_tracks else 0
            
            # Get actual stream indices (FFprobe stream indices, not 0-based)
            available_indices = [track['index'] for track in audio_tracks] if audio_tracks else []
            
            is_valid_track, track_error = validate_track_index(track_index, max_tracks, available_indices)
            if not is_valid_track:
                return self._error_response(track_error)
            
            track_index_int = int(track_index)
        except Exception as e:
            self.logger.error(f"Error validating track index: {e}")
            return self._error_response(f"Invalid track index: {str(e)}")

        # Use console logger
        status_callback = self.log_to_console

        try:
            settings_dict = self.settings.settings # Get all current settings

            # 1. Detect
            ffmpeg_log = detect_silence(
                Path(video_path),
                track_index_int,
                "", # ffmpeg_path (use system)
                settings_dict,
                status_callback
            )

            # 2. Parse
            duration = get_video_duration(Path(video_path), "", status_callback)
            if duration <= 0:
                return self._error_response("Could not determine video duration")
            
            segments = parse_segments(
                ffmpeg_log,
                duration,
                settings_dict,
                status_callback
            )

            self.logger.info(f"Found {len(segments)} segments")
            return {"status": "success", "segments": segments}

        except Exception as e:
            self.logger.error(f"Error detecting silence: {e}", exc_info=True)
            return self._error_response(f"Error detecting silence: {str(e)}")
    
    def run_ai_analysis(
        self,
        video_path: str,
        segments: List[Dict[str, Any]],
        api_key: str,
        whisper_model: str = "base",
        together_model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    ) -> Dict[str, Any]:
        """
        Run AI content analysis on video segments.
        
        This method coordinates the full AI analysis pipeline:
        1. Transcription using local Whisper
        2. Context building (extracting before/after text)
        3. AI analysis using together.ai
        4. Updating segment colors based on decisions
        
        Args:
            video_path: Path to the video file
            segments: List of segment dictionaries from silence detection
            api_key: together.ai API key
            whisper_model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            together_model: together.ai model ID
            
        Returns:
            Dict with updated segments and analysis results, or error dict on failure
        """
        self.logger.info(f"Starting AI analysis for {video_path}")
        self.log_to_console("🤖 Starting AI Content Analysis...\n")
        
        # Validate video path
        is_valid, error_msg = validate_video_path(video_path)
        if not is_valid:
            return self._error_response(error_msg)
        
        # Validate API key
        if not api_key or not api_key.strip():
            return self._error_response("together.ai API key is required")
        
        try:
            # Import AI analysis modules
            from ..ai_analysis.orchestrator import analyze_content, apply_decisions_to_segments
            
            # Status callback that sends messages to UI console
            status_callback = self.log_to_console
            
            # Progress callback
            def progress_callback(stage: str, current: int, total: int):
                message = f"   [{stage}] {current}/{total}\n"
                self.log_to_console(message)
            
            # Run the analysis pipeline
            results = analyze_content(
                video_path=video_path,
                segments=segments,
                api_key=api_key,
                ffmpeg_path="",  # Use system FFmpeg
                whisper_model=whisper_model,
                together_model=together_model,
                prompt_template=None,  # Use default prompt
                context_window_seconds=30.0,
                status_callback=status_callback,
                progress_callback=progress_callback,
                export_path=None  # Could save to temp file if needed
            )
            
            # Check for errors
            if results.errors:
                error_msg = "; ".join(results.errors)
                self.logger.error(f"AI analysis completed with errors: {error_msg}")
                return self._error_response(f"Analysis failed: {error_msg}")
            
            # Apply decisions to segments
            updated_segments = apply_decisions_to_segments(segments, results.decisions)
            
            # Debug: Log first few segments to verify AI decisions are applied
            audible_updated = [s for s in updated_segments if s.get('type') == 'audible'][:5]
            self.logger.info(f"First 5 updated audible segments:")
            for i, seg in enumerate(audible_updated):
                self.logger.info(f"  Segment {i}: start={seg.get('start'):.1f}, keep={seg.get('keep')}, ai_decision={seg.get('ai_decision')}, confidence={seg.get('ai_confidence')}")
            
            self.logger.info(f"AI analysis complete: {results.keep_count} keep, {results.flag_count} flag")
            
            return {
                "status": "success",
                "segments": updated_segments,
                "analysis_summary": {
                    "segments_analyzed": results.segments_analyzed,
                    "keep_count": results.keep_count,
                    "flag_count": results.flag_count,
                    "uncertain_count": results.uncertain_count,
                    "avg_confidence": results.avg_confidence,
                    "processing_time": results.processing_time,
                    "detected_language": results.detected_language,
                    "language_probability": results.language_probability
                }
            }
            
        except ImportError as e:
            error_msg = f"AI analysis dependencies not installed: {str(e)}"
            self.logger.error(error_msg)
            return self._error_response(error_msg)
        except Exception as e:
            self.logger.error(f"AI analysis error: {e}", exc_info=True)
            return self._error_response(f"AI analysis error: {str(e)}")
    
    def get_loadable_file_url(self, file_path: str) -> Optional[str]:
        """
        Returns a URL that the pywebview window can use to load a local file.
        
        Args:
            file_path: Path to file
            
        Returns:
            File URL string or None on error
        """
        try:
            # Normalize the path and convert Windows backslashes to forward slashes
            normalized_path = os.path.normpath(file_path)
            # Convert to forward slashes for file:// URLs
            url_path = normalized_path.replace('\\', '/')
            # On Windows, we need to add an extra slash after file:
            if os.name == 'nt':
                return 'file:///' + url_path
            else:
                return 'file://' + url_path
        except Exception as e:
            self.logger.error(f"Error creating file URL: {e}")
            return None
    
    def create_video_with_audio_tracks(self, video_path: str, enabled_track_indices: List[int]) -> Optional[str]:
        """
        Creates a temporary video file with only the specified audio tracks enabled.
        Uses FFmpeg to mix the selected audio tracks.
        
        Args:
            video_path: Path to source video file
            enabled_track_indices: List of audio track stream indices to include (FFprobe stream indices)
            
        Returns:
            Path to temporary video file, or None on error
        """
        if not enabled_track_indices:
            self.logger.warning("No audio tracks specified, using all tracks")
            return None  # Use original video
        
        self.logger.info(f"Creating video with audio tracks: {enabled_track_indices}")
        
        try:
            import tempfile
            import subprocess
            
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"video_audio_{os.getpid()}_{int(time.time())}.mp4")
            
            # Clean up old temporary files from previous operations
            self._cleanup_old_temp_files(temp_dir)
            
            # Build FFmpeg command to copy video and mix selected audio tracks
            cmd = ["ffmpeg", "-i", video_path]
            
            # Map video stream
            cmd.extend(["-map", "0:v:0"])
            cmd.extend(["-c:v", "copy"])  # Copy video codec
            
            # Handle audio tracks
            if len(enabled_track_indices) > 1:
                # Multiple tracks: need to mix them using amix filter
                # Build filter_complex: [0:1][0:2]amix=inputs=2:duration=longest[aout]
                filter_inputs = "".join([f"[0:{stream_idx}]" for stream_idx in enabled_track_indices])
                filter_complex = f"{filter_inputs}amix=inputs={len(enabled_track_indices)}:duration=longest[aout]"
                cmd.extend(["-filter_complex", filter_complex])
                cmd.extend(["-map", "[aout]"])
                cmd.extend(["-c:a", "aac", "-b:a", "192k"])
            else:
                # Single track: just map and copy
                stream_idx = enabled_track_indices[0]
                cmd.extend(["-map", f"0:{stream_idx}"])
                cmd.extend(["-c:a", "copy"])
            
            cmd.extend(["-y", temp_file])  # -y to overwrite
            
            # Run FFmpeg
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                startupinfo=startupinfo
            )
            
            if result.returncode == 0 and os.path.exists(temp_file):
                self.logger.info(f"Created temporary video: {temp_file}")
                # Track this temp file for cleanup
                self.temp_video_files.append(temp_file)
                return temp_file
            else:
                self.logger.error(f"FFmpeg failed: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating video with audio tracks: {e}", exc_info=True)
            return None
    
    def _cleanup_old_temp_files(self, temp_dir: str, max_age_seconds: int = 3600) -> None:
        """
        Clean up old temporary video files created by this app.
        
        Args:
            temp_dir: Directory to search for temp files
            max_age_seconds: Delete files older than this (default: 1 hour)
        """
        try:
            import glob
            current_time = time.time()
            pattern = os.path.join(temp_dir, "video_audio_*.mp4")
            
            for temp_file in glob.glob(pattern):
                try:
                    # Check file age
                    file_age = current_time - os.path.getmtime(temp_file)
                    if file_age > max_age_seconds:
                        os.remove(temp_file)
                        self.logger.debug(f"Cleaned up old temp file: {temp_file}")
                except (OSError, FileNotFoundError) as e:
                    # File might have been deleted already, ignore
                    self.logger.debug(f"Could not delete temp file {temp_file}: {e}")
        except Exception as e:
            self.logger.warning(f"Error cleaning up temp files: {e}")
    
    def cleanup_temp_files(self) -> None:
        """
        Clean up all temporary video files created during this session.
        Call this when the app is closing or when switching videos.
        """
        for temp_file in self.temp_video_files[:]:  # Copy list to avoid modification during iteration
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    self.logger.debug(f"Deleted temp file: {temp_file}")
            except (OSError, FileNotFoundError) as e:
                self.logger.debug(f"Could not delete temp file {temp_file}: {e}")
        
        # Clear the list
        self.temp_video_files.clear()
        
        # Also clean up any orphaned temp files older than 1 hour
        import tempfile
        temp_dir = tempfile.gettempdir()
        self._cleanup_old_temp_files(temp_dir)
    
    def export_video(self, video_info: Dict[str, Any], segments: List[Dict[str, Any]], 
                     export_settings: Dict[str, Any]) -> Dict[str, str]:
        """
        Receives the video info, segments, and export settings from JavaScript
        and starts the ffmpeg export process.
        
        Args:
            video_info: Video information dictionary
            segments: List of segment dictionaries
            export_settings: Export configuration dictionary
            
        Returns:
            Dict with status and message
        """
        self.logger.info("Received request to export video")

        # Validate inputs
        if not video_info or not video_info.get('filePath'):
            return self._error_response("Invalid video info")
        
        if not segments:
            return self._error_response("No segments provided")
        
        # Validate video path
        video_path = video_info.get('filePath')
        is_valid, error_msg = validate_video_path(video_path)
        if not is_valid:
            return self._error_response(error_msg)
        
        # Validate trim values if provided
        trim_start = export_settings.get('trim_start')
        trim_end = export_settings.get('trim_end')
        duration = video_info.get('duration', 0)
        
        if trim_start or trim_end:
            is_valid_trim, trim_error = validate_trim_values(trim_start or 0, trim_end, duration)
            if not is_valid_trim:
                return self._error_response(trim_error)
        
        # 1. Get save location if not provided in settings
        save_path = export_settings.get('save_path')
        if not save_path:
            save_path = self.select_save_destination()
            if not save_path:
                self.logger.info("Export cancelled by user (no save folder)")
                return {"status": "cancelled", "message": "No save folder selected."}

        # 2. Get settings from our core files
        settings_dict = self.settings.settings
        
        # 3. Get encoder and format from export_settings
        encoder_name = export_settings.get('encoder', 'CPU (x264)')
        output_format = export_settings.get('format', 'mp4').lower()
        
        # 4. Get video parameters based on encoder
        # Get encoder params from config.py (ENCODER_OPTIONS)
        video_params = ""
        if encoder_name == "Automatic (Best GPU)":
            # Find the best available GPU encoder
            for enc in self.available_encoders:
                if "NVIDIA" in enc or "AMD" in enc or "Intel" in enc:
                    params_tuple = ENCODER_OPTIONS.get(enc)
                    if params_tuple:
                        video_params = params_tuple[1]
                        self.log_to_console(f"Auto-selected encoder: {enc}")
                        break
            if not video_params:  # Fallback to CPU
                video_params = ENCODER_OPTIONS.get("CPU (x264)")[1]
                self.log_to_console("Auto-selected encoder: CPU (x264)")
        else:
            # Get the specific params for the selected encoder
            params_tuple = ENCODER_OPTIONS.get(encoder_name)
            if params_tuple:
                video_params = params_tuple[1]
            else:  # Fallback
                self.log_to_console(f"Error: Could not find settings for {encoder_name}. Defaulting to CPU.")
                video_params = ENCODER_OPTIONS.get("CPU (x264)")[1]

        # 5. Get trim settings
        trim_start = export_settings.get('trim_start')
        trim_end = export_settings.get('trim_end')
        
        # Use console logger
        status_callback = self.log_to_console
        
        self.log_to_console(f"Starting export with encoder: {encoder_name}...")
        
        def progress_callback(percentage, eta, speed):
            # Send progress updates to JavaScript
            self.logger.debug(f"Progress: {percentage:.2f}%, ETA: {eta}, Speed: {speed}x")
            if self.window:
                try:
                    # Escape single quotes in ETA string
                    eta_escaped = eta.replace("'", "\\'")
                    self.window.evaluate_js(f"window.updateProgress({percentage}, '{eta_escaped}', {speed});")
                except Exception as e:
                    self.logger.warning(f"Error sending progress update: {e}")

        try:
            # 6. Get audio tracks safely (handle videos without audio)
            audio_tracks = video_info.get('audioTracks', [])
            if not audio_tracks:
                # Video has no audio tracks - use default index 0
                silence_track_index = 0
                self.logger.warning("Video has no audio tracks, using default track index 0")
            else:
                # Safe access for audio track index
                silence_track_index = audio_tracks[0].get('index', 0)
            
            # 7. Call our existing core function!
            process_video_logic(
                video_path=video_info['filePath'],
                output_dir=save_path,
                output_format=output_format,
                video_params=video_params,
                all_audio_tracks=audio_tracks,
                silence_track_index=silence_track_index,
                ffmpeg_path="", # Use system path
                ffprobe_path="", # Use system path
                settings=settings_dict,
                status_callback=status_callback,
                progress_callback=progress_callback,
                segments=segments, # Pass in the user-modified segments!
                trim_start=float(trim_start) if trim_start else 0.0,
                trim_end=float(trim_end) if trim_end else None
            )

            self.logger.info(f"Export complete! Saved to {save_path}")
            return {"status": "success", "message": f"TooBoooring Studio - Export complete! Saved to {save_path}"}

        except Exception as e:
            self.logger.error(f"Export failed: {e}", exc_info=True)
            self.log_to_console(f"Export failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def export_video_cuts(self, video_info: Dict[str, Any], segments: List[Dict[str, Any]], 
                          export_settings: Dict[str, Any]) -> Dict[str, str]:
        """
        Exports each audible segment as a separate video file in a folder named after the video.
        
        Args:
            video_info: Video information dictionary
            segments: List of audible segment dictionaries (only segments with keep=true)
            export_settings: Export configuration dictionary
            
        Returns:
            Dict with status and message
        """
        self.logger.info("Received request to export video cuts")
        
        # Validate inputs
        if not video_info or not video_info.get('filePath'):
            return self._error_response("Invalid video info")
        
        if not segments:
            return self._error_response("No segments provided")
        
        # Validate video path
        video_path = video_info.get('filePath')
        is_valid, error_msg = validate_video_path(video_path)
        if not is_valid:
            return self._error_response(error_msg)
        
        # Validate trim values if provided
        trim_start = export_settings.get('trim_start')
        trim_end = export_settings.get('trim_end')
        duration = video_info.get('duration', 0)
        
        if trim_start or trim_end:
            is_valid_trim, trim_error = validate_trim_values(trim_start or 0, trim_end, duration)
            if not is_valid_trim:
                return self._error_response(trim_error)
        
        # 1. Get save location
        save_path = export_settings.get('save_path')
        if not save_path:
            save_path = self.select_save_destination()
            if not save_path:
                self.logger.info("Export cancelled by user (no save folder)")
                return {"status": "cancelled", "message": "No save folder selected."}
        
        # 2. Create folder named after video (without extension)
        video_name = Path(video_info['fileName']).stem  # Get filename without extension
        cuts_folder = Path(save_path) / video_name
        
        try:
            cuts_folder.mkdir(parents=True, exist_ok=True)
            self.log_to_console(f"📁 Created folder: {cuts_folder}\n")
        except Exception as e:
            self.logger.error(f"Error creating cuts folder: {e}")
            return self._error_response(f"Could not create output folder: {str(e)}")
        
        # 3. Get settings
        settings_dict = self.settings.settings
        encoder_name = export_settings.get('encoder', 'CPU (x264)')
        output_format = export_settings.get('format', 'mp4').lower()
        
        # 4. Get encoder parameters
        video_params = ""
        if encoder_name == "Automatic (Best GPU)":
            for enc in self.available_encoders:
                if "NVIDIA" in enc or "AMD" in enc or "Intel" in enc:
                    params_tuple = ENCODER_OPTIONS.get(enc)
                    if params_tuple:
                        video_params = params_tuple[1]
                        self.log_to_console(f"Auto-selected encoder: {enc}\n")
                        break
            if not video_params:
                video_params = ENCODER_OPTIONS.get("CPU (x264)")[1]
                self.log_to_console("Auto-selected encoder: CPU (x264)\n")
        else:
            params_tuple = ENCODER_OPTIONS.get(encoder_name)
            if params_tuple:
                video_params = params_tuple[1]
            else:
                self.log_to_console(f"Error: Could not find settings for {encoder_name}. Defaulting to CPU.\n")
                video_params = ENCODER_OPTIONS.get("CPU (x264)")[1]
        
        # 5. Get trim settings
        trim_start = export_settings.get('trim_start')
        trim_end = export_settings.get('trim_end')
        
        status_callback = self.log_to_console
        
        def progress_callback(percentage, eta, speed):
            # Send progress updates to JavaScript
            self.logger.debug(f"Progress: {percentage:.2f}%, ETA: {eta}, Speed: {speed}x")
            if self.window:
                try:
                    eta_escaped = eta.replace("'", "\\'")
                    self.window.evaluate_js(f"window.updateProgress({percentage}, '{eta_escaped}', {speed});")
                except Exception as e:
                    self.logger.warning(f"Error sending progress update: {e}")
        
        try:
            import subprocess
            import shlex
            
            total_cuts = len(segments)
            self.log_to_console(f"📹 Exporting {total_cuts} cut(s)...\n")
            
            # Process each segment
            for i, segment in enumerate(segments, 1):
                segment_start = segment['start']
                segment_end = segment['end']
                
                # Apply trim offset if specified
                if trim_start:
                    segment_start += float(trim_start)
                    segment_end += float(trim_start)
                
                # Check if segment is within trim_end limit
                if trim_end and segment_start >= float(trim_end):
                    continue  # Skip segments beyond trim_end
                if trim_end and segment_end > float(trim_end):
                    segment_end = float(trim_end)  # Clip to trim_end
                
                # Recalculate duration after trim adjustments
                segment_duration = segment_end - segment_start
                
                # Skip if duration is invalid
                if segment_duration <= 0:
                    self.log_to_console(f"⚠️ Skipping cut {i}: Invalid duration ({segment_duration:.2f}s)\n")
                    continue
                
                # Generate output filename
                cut_filename = f"cut_{i:03d}.{output_format}"
                output_file = cuts_folder / cut_filename
                
                self.log_to_console(f"✂️ Exporting cut {i}/{total_cuts}: {cut_filename} ({segment_start:.2f}s - {segment_end:.2f}s, {segment_duration:.2f}s)\n")
                
                # Update progress: overall progress across all cuts
                overall_progress = ((i - 1) / total_cuts) * 100
                progress_callback(overall_progress, f"Cut {i}/{total_cuts}", 0)
                
                # Build FFmpeg command to extract this segment
                ffmpeg_executable = "ffmpeg"  # Use system PATH
                cmd = [
                    str(ffmpeg_executable),
                    "-y",  # Overwrite output
                    "-hide_banner",
                    "-ss", str(segment_start),  # Start time
                    "-i", str(video_path),  # Input file
                    "-t", str(segment_duration),  # Duration
                ]
                
                # Get input file extension (without dot)
                input_ext = Path(video_path).suffix[1:].lower() if Path(video_path).suffix else ""
                
                # If we need to re-encode (for format conversion or codec changes)
                if output_format != input_ext:
                    # Need to re-encode
                    video_args = shlex.split(video_params)
                    cmd.extend(video_args)
                    
                    # Audio codec
                    if output_format.lower() == "mp4":
                        cmd.extend(["-c:a", "aac", "-b:a", "192k"])
                    else:
                        cmd.extend(["-c:a", "copy"])
                    
                    # Pixel format for MP4
                    if output_format.lower() == "mp4":
                        cmd.extend(["-pix_fmt", "yuv420p"])
                else:
                    # Just copy streams (much faster)
                    cmd.extend(["-c", "copy"])
                
                cmd.append(str(output_file))
                
                # Run FFmpeg
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    startupinfo=startupinfo
                )
                
                if result.returncode != 0:
                    error_msg = f"Failed to export cut {i}: {result.stderr[:200]}"
                    self.logger.error(error_msg)
                    self.log_to_console(f"❌ {error_msg}\n")
                    # Continue with next cut instead of failing completely
                    continue
                
                self.log_to_console(f"✅ Cut {i}/{total_cuts} exported: {cut_filename}\n")
            
            # Final progress update
            progress_callback(100, "Complete", 0)
            
            self.logger.info(f"Export cuts complete! Saved {total_cuts} cut(s) to {cuts_folder}")
            return {
                "status": "success",
                "message": f"TooBoooring Studio - Export complete! {total_cuts} cut(s) saved to:\n{cuts_folder}"
            }
        
        except Exception as e:
            self.logger.error(f"Export cuts failed: {e}", exc_info=True)
            self.log_to_console(f"Export failed: {str(e)}\n")
            return {"status": "error", "message": str(e)}
    
    def export_edl(self, video_info: Dict[str, Any], segments: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Exports an Edit Decision List (EDL) file for DaVinci Resolve/Premiere Pro.
        
        Args:
            video_info: Video information dictionary
            segments: List of audible segment dictionaries (only segments with keep=true)
            
        Returns:
            Dict with status and message/file_path
        """
        self.logger.info("Received request to export EDL file")
        
        # Validate inputs
        if not video_info or not video_info.get('filePath'):
            return self._error_response("Invalid video info")
        
        if not segments:
            return self._error_response("No segments provided")
        
        # Validate video path
        video_path = video_info.get('filePath')
        is_valid, error_msg = validate_video_path(video_path)
        if not is_valid:
            return self._error_response(error_msg)
        
        # Get save location
        save_path = self.select_save_destination()
        if not save_path:
            self.logger.info("EDL export cancelled by user (no save folder)")
            return {"status": "cancelled", "message": "No save folder selected."}
        
        try:
            # Get video frame rate (default to 30fps if not available)
            fps = 30.0  # Default
            try:
                # Try to get actual frame rate from video
                import subprocess
                ffprobe_executable = "ffprobe"
                cmd = [
                    str(ffprobe_executable),
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=r_frame_rate",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(video_path)
                ]
                
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    startupinfo=startupinfo
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    # Parse frame rate (format: "30/1" or "30000/1001")
                    frame_rate_str = result.stdout.strip()
                    if '/' in frame_rate_str:
                        num, den = map(int, frame_rate_str.split('/'))
                        fps = num / den if den > 0 else 30.0
                    else:
                        fps = float(frame_rate_str) if frame_rate_str else 30.0
                    
                    self.log_to_console(f"Detected frame rate: {fps:.2f} fps\n")
                else:
                    self.log_to_console(f"Using default frame rate: {fps:.2f} fps\n")
            except Exception as e:
                self.logger.warning(f"Could not detect frame rate, using default: {e}")
                self.log_to_console(f"Using default frame rate: {fps:.2f} fps\n")
            
            # Generate EDL filename
            video_name = Path(video_info['fileName']).stem
            edl_filename = f"{video_name}_cuts.edl"
            edl_path = Path(save_path) / edl_filename
            
            # Generate EDL content
            edl_lines = []
            
            # EDL Header
            edl_lines.append("TITLE: Silence Cuts")
            edl_lines.append(f"FCM: NON-DROP FRAME")
            edl_lines.append("")
            
            # Get video filename for reel name (EDL format requirement)
            # Use full filename stem (without extension) but limit to 8 chars for EDL compatibility
            # Resolve matches reel name to media file name, so we want it to match as closely as possible
            video_stem = Path(video_info['fileName']).stem
            reel_name = video_stem[:8].upper() if len(video_stem) >= 8 else video_stem.upper()
            if not reel_name:
                reel_name = "VIDEO"
            
            # Log the reel name for debugging
            self.log_to_console(f"Using reel name: '{reel_name}' (from video: '{video_stem}')\n")
            self.log_to_console(f"⚠️ IMPORTANT: Make sure your video file name starts with '{reel_name}' or matches this reel name in Resolve!\n")
            
            # Get audio tracks info from video
            audio_tracks = video_info.get('audioTracks', [])
            num_audio_tracks = len(audio_tracks) if audio_tracks else 1  # Default to 1 if unknown
            
            # Calculate timeline position (record in/out)
            timeline_start = 0.0
            
            # Generate edit entries for each segment
            for i, segment in enumerate(segments, 1):
                source_start = segment['start']
                source_end = segment['end']
                duration = source_end - source_start
                
                # Calculate timeline positions - ensure sequential placement with no gaps
                record_start = timeline_start
                record_end = timeline_start + duration
                
                # Convert seconds to timecode (HH:MM:SS:FF format) with better precision
                def seconds_to_timecode(seconds, fps):
                    """Convert seconds to EDL timecode format HH:MM:SS:FF with frame-accurate rounding"""
                    # Use round() for better accuracy instead of int()
                    # Ensure we don't go negative
                    if seconds < 0:
                        seconds = 0
                    total_frames = round(seconds * fps)
                    fps_int = int(round(fps))
                    if fps_int <= 0:
                        fps_int = 30  # Safety fallback
                    hours = total_frames // (fps_int * 3600)
                    minutes = (total_frames // (fps_int * 60)) % 60
                    secs = (total_frames // fps_int) % 60
                    frames = total_frames % fps_int
                    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"
                
                source_in = seconds_to_timecode(source_start, fps)
                source_out = seconds_to_timecode(source_end, fps)
                record_in = seconds_to_timecode(record_start, fps)
                record_out = seconds_to_timecode(record_end, fps)
                
                # EDL format: Edit# Reel Track EditType SourceIn SourceOut RecordIn RecordOut
                # Format: "001  REEL     V     C        00:00:00:00 00:00:10:15 00:00:00:00 00:00:10:15"
                # Important: Each edit must have a unique edit number, and record times must be sequential
                
                # Add video track edit - use unique edit number for each segment
                edit_line = f"{i:03d}  {reel_name:<8s} V     C        {source_in} {source_out} {record_in} {record_out}"
                edl_lines.append(edit_line)
                
                # Add audio track edits (EDL supports multiple audio tracks)
                # EDL format: First audio track is "A", subsequent tracks are "A2", "A3", etc.
                # All tracks for the same edit use the same edit number
                for audio_idx in range(num_audio_tracks):
                    if audio_idx == 0:
                        audio_track_letter = "A"
                    else:
                        audio_track_letter = f"A{audio_idx + 1}"
                    # Use same edit number as video track for this segment
                    audio_edit_line = f"{i:03d}  {reel_name:<8s} {audio_track_letter:<6s} C        {source_in} {source_out} {record_in} {record_out}"
                    edl_lines.append(audio_edit_line)
                
                # Update timeline position for next segment - ensure no gaps
                # The next segment's record_in should equal this segment's record_out
                timeline_start = record_end
            
            # Write EDL file
            edl_content = "\n".join(edl_lines)
            with open(edl_path, 'w', encoding='utf-8') as f:
                f.write(edl_content)
            
            self.logger.info(f"EDL file exported: {edl_path}")
            self.log_to_console(f"✅ EDL file generated: {edl_filename}\n")
            self.log_to_console(f"📁 Location: {edl_path}\n")
            self.log_to_console(f"📊 Contains {len(segments)} cut(s)\n")
            self.log_to_console(f"\n💡 Import Instructions:\n")
            self.log_to_console(f"1. Open DaVinci Resolve\n")
            self.log_to_console(f"2. Import your video file into Media Pool FIRST\n")
            self.log_to_console(f"3. File → Import → Timeline → Import EDL (Pre-conformed EDL)\n")
            self.log_to_console(f"4. Select: {edl_filename}\n")
            self.log_to_console(f"5. In import dialog:\n")
            self.log_to_console(f"   - Set timeline frame rate to {fps:.2f} fps\n")
            self.log_to_console(f"   - Check reel name matches: '{reel_name}'\n")
            self.log_to_console(f"   - If reel not found, manually link to your video file\n")
            self.log_to_console(f"6. Click Import\n")
            self.log_to_console(f"\n⚠️ TROUBLESHOOTING:\n")
            self.log_to_console(f"If you see one continuous clip instead of cuts:\n")
            self.log_to_console(f"- Make sure video is imported to Media Pool BEFORE importing EDL\n")
            self.log_to_console(f"- Check that reel name '{reel_name}' matches your video file\n")
            self.log_to_console(f"- Try renaming your video file to start with '{reel_name}'\n")
            self.log_to_console(f"- Or manually link the reel in the import dialog\n")
            
            return {
                "status": "success",
                "message": f"TooBoooring Studio - EDL file exported successfully!\n\nFile: {edl_filename}\nLocation: {edl_path}",
                "file_path": str(edl_path)
            }
        
        except Exception as e:
            self.logger.error(f"EDL export failed: {e}", exc_info=True)
            self.log_to_console(f"EDL export failed: {str(e)}\n")
            return {"status": "error", "message": str(e)}
    
    def export_fcp_xml(self, video_info: Dict[str, Any], segments: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Exports a Final Cut Pro XML file for DaVinci Resolve/Premiere Pro.
        FCP XML is more reliable than EDL and better supports audio tracks.
        
        Args:
            video_info: Video information dictionary
            segments: List of audible segment dictionaries (only segments with keep=true)
            
        Returns:
            Dict with status and message/file_path
        """
        self.logger.info("Received request to export FCP XML file")
        
        # Validate inputs
        if not video_info or not video_info.get('filePath'):
            return self._error_response("Invalid video info")
        
        if not segments:
            return self._error_response("No segments provided")
        
        # Validate video path
        video_path = video_info.get('filePath')
        is_valid, error_msg = validate_video_path(video_path)
        if not is_valid:
            return self._error_response(error_msg)
        
        # Get save location
        save_path = self.select_save_destination()
        if not save_path:
            self.logger.info("FCP XML export cancelled by user (no save folder)")
            return {"status": "cancelled", "message": "No save folder selected."}
        
        try:
            import xml.etree.ElementTree as ET
            from xml.dom import minidom
            
            # Get video frame rate and other properties
            fps = 30.0  # Default
            video_width = 1920
            video_height = 1080
            timebase = "30"
            ntsc = "FALSE"
            
            try:
                # Get video properties using ffprobe
                import subprocess
                ffprobe_executable = "ffprobe"
                # Get frame rate first (separate call for cleaner parsing)
                cmd_fps = [
                    str(ffprobe_executable),
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=r_frame_rate",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(video_path)
                ]
                
                # Get dimensions (separate call)
                cmd_dim = [
                    str(ffprobe_executable),
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(video_path)
                ]
                
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                # Get frame rate
                result_fps = subprocess.run(
                    cmd_fps,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    startupinfo=startupinfo
                )
                
                if result_fps.returncode == 0 and result_fps.stdout.strip():
                    frame_rate_str = result_fps.stdout.strip()
                    try:
                        if '/' in frame_rate_str:
                            parts = frame_rate_str.split('/')
                            if len(parts) == 2:
                                num = int(parts[0].strip())
                                den = int(parts[1].strip())
                                fps = num / den if den > 0 else 30.0
                            else:
                                fps = float(frame_rate_str) if frame_rate_str else 30.0
                        else:
                            fps = float(frame_rate_str) if frame_rate_str else 30.0
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Could not parse frame rate '{frame_rate_str}': {e}")
                        fps = 30.0
                
                # Get dimensions
                result_dim = subprocess.run(
                    cmd_dim,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    startupinfo=startupinfo
                )
                
                if result_dim.returncode == 0 and result_dim.stdout.strip():
                    dim_lines = result_dim.stdout.strip().split('\n')
                    if len(dim_lines) > 0 and dim_lines[0].strip():
                        try:
                            video_width = int(dim_lines[0].strip())
                        except ValueError:
                            pass
                    if len(dim_lines) > 1 and dim_lines[1].strip():
                        try:
                            video_height = int(dim_lines[1].strip())
                        except ValueError:
                            pass
                    
                    # Set timebase (frames per second as string)
                    timebase = str(int(round(fps)))
                    # Check if NTSC (29.97, 59.94, etc.)
                    if abs(fps - 29.97) < 0.1 or abs(fps - 59.94) < 0.1 or abs(fps - 23.976) < 0.1:
                        ntsc = "TRUE"
                    
                    self.log_to_console(f"Detected: {fps:.2f} fps, {video_width}x{video_height}\n")
                else:
                    self.log_to_console(f"Using defaults: {fps:.2f} fps, {video_width}x{video_height}\n")
            except Exception as e:
                self.logger.warning(f"Could not detect video properties, using defaults: {e}")
                self.log_to_console(f"Using defaults: {fps:.2f} fps\n")
            
            # Get audio tracks
            audio_tracks = video_info.get('audioTracks', [])
            num_audio_tracks = len(audio_tracks) if audio_tracks else 1
            
            # Store audio track stream indices for proper audio stream mapping
            audio_stream_indices = []
            if audio_tracks:
                for track in audio_tracks:
                    # Get the stream index (FFprobe index, typically 1-based for first audio)
                    stream_idx = track.get('index', len(audio_stream_indices) + 1)
                    audio_stream_indices.append(stream_idx)
            else:
                # Default to first audio stream if no track info
                audio_stream_indices = [1]
            
            # Generate XML filename
            video_name = Path(video_info['fileName']).stem
            xml_filename = f"{video_name}_cuts.xml"
            xml_path = Path(save_path) / xml_filename
            
            # Create XML root
            root = ET.Element("xmeml")
            root.set("version", "5")
            
            # Create sequence
            sequence = ET.SubElement(root, "sequence")
            ET.SubElement(sequence, "name").text = f"{video_name} - Silence Cuts"
            ET.SubElement(sequence, "duration").text = "0"  # Will be calculated
            
            # Rate (frame rate)
            rate = ET.SubElement(sequence, "rate")
            ET.SubElement(rate, "timebase").text = timebase
            ET.SubElement(rate, "ntsc").text = ntsc
            
            # Timecode
            timecode = ET.SubElement(sequence, "timecode")
            timecode_rate = ET.SubElement(timecode, "rate")
            ET.SubElement(timecode_rate, "timebase").text = timebase
            ET.SubElement(timecode_rate, "ntsc").text = ntsc
            ET.SubElement(timecode, "string").text = "01:00:00:00"
            ET.SubElement(timecode, "frame").text = "0"
            
            # Media
            media = ET.SubElement(sequence, "media")
            
            # Define the source file FIRST (before video/audio tracks)
            # This is critical - file must be defined before it's referenced
            video_file_path = Path(video_path)
            file_id = "file-1"
            file_elem = ET.Element("file")
            file_elem.set("id", file_id)
            ET.SubElement(file_elem, "name").text = video_file_path.name
            
            # Add pathurl - Resolve needs this to find the file
            pathurl = ET.SubElement(file_elem, "pathurl")
            # Convert Windows path to file:// URL format
            abs_path = video_file_path.resolve()
            # Use forward slashes and ensure proper file:// format
            path_str = str(abs_path).replace('\\', '/')
            # Windows paths need file:/// (three slashes), Unix needs file:// (two slashes)
            if os.name == 'nt':
                pathurl.text = f"file:///{path_str}"
            else:
                pathurl.text = f"file://{path_str}"
            
            # Also add path element (some XML readers prefer this)
            path_elem = ET.SubElement(file_elem, "path")
            path_elem.text = str(abs_path)
            
            # File rate
            file_rate = ET.SubElement(file_elem, "rate")
            ET.SubElement(file_rate, "timebase").text = timebase
            ET.SubElement(file_rate, "ntsc").text = ntsc
            
            # Duration (total frames)
            total_duration = video_info.get('duration', 0)
            total_frames = int(round(total_duration * fps))
            ET.SubElement(file_elem, "duration").text = str(total_frames)
            
            # Media info
            media_info = ET.SubElement(file_elem, "media")
            video_media = ET.SubElement(media_info, "video")
            sample_char = ET.SubElement(video_media, "samplecharacteristics")
            ET.SubElement(sample_char, "width").text = str(video_width)
            ET.SubElement(sample_char, "height").text = str(video_height)
            ET.SubElement(sample_char, "pixelaspectratio").text = "square"
            ET.SubElement(sample_char, "fielddominance").text = "none"
            rate_elem = ET.SubElement(sample_char, "rate")
            ET.SubElement(rate_elem, "timebase").text = timebase
            ET.SubElement(rate_elem, "ntsc").text = ntsc
            
            # Audio media info
            audio_media = ET.SubElement(media_info, "audio")
            for audio_idx in range(num_audio_tracks):
                audio_sample = ET.SubElement(audio_media, "samplecharacteristics")
                ET.SubElement(audio_sample, "depth").text = "16"
                # Get actual sample rate from track info if available
                sample_rate = "48000"  # Default
                if audio_tracks and audio_idx < len(audio_tracks):
                    track_info = audio_tracks[audio_idx]
                    # sample_rate might be in Hz, convert to string
                    sr = track_info.get('sample_rate', '48000')
                    if isinstance(sr, str) and 'kHz' in sr:
                        # Convert "48kHz" to "48000"
                        sample_rate = str(int(float(sr.replace('kHz', '').strip()) * 1000))
                    elif isinstance(sr, (int, float)):
                        sample_rate = str(int(sr))
                    else:
                        sample_rate = str(sr).replace('kHz', '').replace(' ', '')
                ET.SubElement(audio_sample, "samplerate").text = sample_rate
                
                # Add channel count for each audio stream
                channel_count = 2  # Default stereo
                if audio_tracks and audio_idx < len(audio_tracks):
                    channel_count = audio_tracks[audio_idx].get('channels', 2)
                ET.SubElement(audio_sample, "channelcount").text = str(channel_count)
            
            # Add file to media FIRST (before video/audio sections)
            # This is critical - file must be first child of <media>
            media.insert(0, file_elem)
            
            # Format element (required by Resolve)
            format_elem = ET.SubElement(media, "format")
            format_sample = ET.SubElement(format_elem, "samplecharacteristics")
            ET.SubElement(format_sample, "width").text = str(video_width)
            ET.SubElement(format_sample, "height").text = str(video_height)
            ET.SubElement(format_sample, "pixelaspectratio").text = "square"
            ET.SubElement(format_sample, "fielddominance").text = "none"
            format_rate = ET.SubElement(format_sample, "rate")
            ET.SubElement(format_rate, "timebase").text = timebase
            ET.SubElement(format_rate, "ntsc").text = ntsc
            
            # Video section (after file definition)
            video = ET.SubElement(media, "video")
            video_track = ET.SubElement(video, "track")
            
            # Audio section (after file definition)
            audio = ET.SubElement(media, "audio")
            
            # Calculate total timeline duration
            timeline_duration = sum(seg['end'] - seg['start'] for seg in segments)
            timeline_frames = int(round(timeline_duration * fps))
            sequence.find("duration").text = str(timeline_frames)
            
            # Create audio track elements (one per audio track)
            audio_track_elements = []
            for audio_idx in range(num_audio_tracks):
                audio_track_elem = ET.SubElement(audio, "track")
                # Set track output channel (required for audio to work)
                ET.SubElement(audio_track_elem, "outputchannelindex").text = str(audio_idx + 1)
                audio_track_elements.append(audio_track_elem)
            
            # Add clips to video track
            timeline_start = 0.0
            for i, segment in enumerate(segments):
                source_start = segment['start']
                source_end = segment['end']
                duration = source_end - source_start
                
                record_start = timeline_start
                record_end = timeline_start + duration
                
                # Convert to frames
                source_start_frames = int(round(source_start * fps))
                source_end_frames = int(round(source_end * fps))
                record_start_frames = int(round(record_start * fps))
                record_end_frames = int(round(record_end * fps))
                
                # Video clip
                video_clipitem = ET.SubElement(video_track, "clipitem")
                video_clipitem.set("id", f"clip-video-{i+1}")
                ET.SubElement(video_clipitem, "name").text = video_file_path.name
                ET.SubElement(video_clipitem, "duration").text = str(record_end_frames - record_start_frames)
                
                # File reference (MUST be first child of clipitem for Resolve)
                file_ref = ET.SubElement(video_clipitem, "file")
                file_ref.set("id", file_id)
                
                # In/Out points (MUST come before sourcetimecode for Resolve)
                ET.SubElement(video_clipitem, "in").text = str(source_start_frames)
                ET.SubElement(video_clipitem, "out").text = str(source_end_frames)
                ET.SubElement(video_clipitem, "start").text = str(record_start_frames)
                ET.SubElement(video_clipitem, "end").text = str(record_end_frames)
                
                # Rate (required by Resolve)
                clip_rate = ET.SubElement(video_clipitem, "rate")
                ET.SubElement(clip_rate, "timebase").text = timebase
                ET.SubElement(clip_rate, "ntsc").text = ntsc
                
                # Source timecode
                source_tc = ET.SubElement(video_clipitem, "sourcetimecode")
                source_tc_rate = ET.SubElement(source_tc, "rate")
                ET.SubElement(source_tc_rate, "timebase").text = timebase
                ET.SubElement(source_tc_rate, "ntsc").text = ntsc
                ET.SubElement(source_tc, "string").text = self._frames_to_timecode(source_start_frames, fps)
                ET.SubElement(source_tc, "frame").text = str(source_start_frames)
                
                # Enabled (required by Resolve)
                ET.SubElement(video_clipitem, "enabled").text = "TRUE"
                
                # Audio clips for each track - add to the corresponding track element
                for audio_idx in range(num_audio_tracks):
                    audio_track_elem = audio_track_elements[audio_idx]
                    
                    audio_clipitem = ET.SubElement(audio_track_elem, "clipitem")
                    audio_clipitem.set("id", f"clip-audio-{i+1}-{audio_idx}")
                    ET.SubElement(audio_clipitem, "name").text = video_file_path.name
                    ET.SubElement(audio_clipitem, "duration").text = str(record_end_frames - record_start_frames)
                    
                    # File reference (MUST be first child of clipitem for Resolve)
                    audio_file_ref = ET.SubElement(audio_clipitem, "file")
                    audio_file_ref.set("id", file_id)
                    
                    # Specify which audio stream to use from the file (critical for multi-track audio)
                    # FCP XML uses 0-based indexing for streams (0=first audio, 1=second audio, etc.)
                    # But we need to map FFprobe's stream index to FCP's audio stream index
                    if audio_idx < len(audio_stream_indices):
                        # FFprobe index is the actual stream index in the file
                        # For FCP XML, we need to count only audio streams (skip video stream)
                        # If video is stream 0, first audio is stream 1, but FCP XML audio streamindex is 0-based
                        ffprobe_index = audio_stream_indices[audio_idx]
                        # FCP XML streamindex for audio: 0 = first audio stream, 1 = second audio stream, etc.
                        # We use audio_idx directly as it's already 0-based
                        ET.SubElement(audio_file_ref, "streamindex").text = str(audio_idx)
                    
                    # In/Out points (MUST come before sourcetimecode for Resolve)
                    ET.SubElement(audio_clipitem, "in").text = str(source_start_frames)
                    ET.SubElement(audio_clipitem, "out").text = str(source_end_frames)
                    ET.SubElement(audio_clipitem, "start").text = str(record_start_frames)
                    ET.SubElement(audio_clipitem, "end").text = str(record_end_frames)
                    
                    # Rate (required by Resolve)
                    audio_clip_rate = ET.SubElement(audio_clipitem, "rate")
                    ET.SubElement(audio_clip_rate, "timebase").text = timebase
                    ET.SubElement(audio_clip_rate, "ntsc").text = ntsc
                    
                    # Source timecode
                    audio_source_tc = ET.SubElement(audio_clipitem, "sourcetimecode")
                    audio_tc_rate = ET.SubElement(audio_source_tc, "rate")
                    ET.SubElement(audio_tc_rate, "timebase").text = timebase
                    ET.SubElement(audio_tc_rate, "ntsc").text = ntsc
                    ET.SubElement(audio_source_tc, "string").text = self._frames_to_timecode(source_start_frames, fps)
                    ET.SubElement(audio_source_tc, "frame").text = str(source_start_frames)
                    
                    # Enabled (required by Resolve)
                    ET.SubElement(audio_clipitem, "enabled").text = "TRUE"
                    
                    # Audio channel configuration (required for audio to work)
                    # Get channel count from audio track info
                    channel_count = 2  # Default to stereo
                    if audio_tracks and audio_idx < len(audio_tracks):
                        track_info = audio_tracks[audio_idx]
                        channel_count = track_info.get('channels', 2)
                    
                    channelcount = ET.SubElement(audio_clipitem, "channelcount")
                    channelcount.text = str(channel_count)
                    
                    # Link to video clip for sync (Resolve needs this)
                    # The link element structure is critical for audio/video sync
                    # Note: Some FCP XML versions don't require link, but Resolve often does
                    # IMPORTANT: clipindex should be 0-based (i), not 1-based (i+1)
                    link_elem = ET.SubElement(audio_clipitem, "link")
                    link_elem.set("linkclipref", f"clip-video-{i+1}")
                    ET.SubElement(link_elem, "mediatype").text = "video"
                    ET.SubElement(link_elem, "trackindex").text = "1"
                    ET.SubElement(link_elem, "clipindex").text = str(i)  # 0-based index
                    
                    # Audio output mapping (maps to track output)
                    # This tells Resolve which output channel to use
                    outputchannelindex = ET.SubElement(audio_clipitem, "outputchannelindex")
                    outputchannelindex.text = str(audio_idx + 1)
                    
                    # Add audio source channel mapping (may be required for Resolve)
                    # This maps source channels to output channels
                    sourcechannel = ET.SubElement(audio_clipitem, "sourcechannel")
                    sourcechannel.text = str(audio_idx + 1)
                
                # Update timeline position for next clip (CRITICAL - must be after all clips for this segment)
                timeline_start = record_end
            
            # Format XML with proper indentation
            xml_str = ET.tostring(root, encoding='unicode')
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent="  ")
            
            # Write XML file
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)
            
            self.logger.info(f"FCP XML file exported: {xml_path}")
            self.log_to_console(f"✅ FCP XML file generated: {xml_filename}\n")
            self.log_to_console(f"📁 Location: {xml_path}\n")
            self.log_to_console(f"📊 Contains {len(segments)} cut(s) with {num_audio_tracks} audio track(s)\n")
            self.log_to_console(f"🎬 Frame rate: {fps:.2f} fps\n")
            self.log_to_console(f"\n💡 Import Instructions:\n")
            self.log_to_console(f"1. Open DaVinci Resolve\n")
            self.log_to_console(f"2. IMPORTANT: Import your video file to Media Pool FIRST\n")
            self.log_to_console(f"   - Right-click in Media Pool → Import Media\n")
            self.log_to_console(f"   - Select: {video_file_path.name}\n")
            self.log_to_console(f"3. File → Import → Timeline → Timeline... (Ctrl+Shift+I)\n")
            self.log_to_console(f"4. Select: {xml_filename}\n")
            self.log_to_console(f"5. In import dialog:\n")
            self.log_to_console(f"   - Set timeline frame rate to {fps:.2f} fps\n")
            self.log_to_console(f"   - If video shows as 'Offline', click 'Relink Media'\n")
            self.log_to_console(f"   - Browse and select: {video_file_path.name}\n")
            self.log_to_console(f"   - Resolve will link all clips to this file\n")
            self.log_to_console(f"6. Click Import\n")
            self.log_to_console(f"\n⚠️ TROUBLESHOOTING:\n")
            self.log_to_console(f"If video doesn't appear on timeline:\n")
            self.log_to_console(f"1. Make sure video is in Media Pool BEFORE importing XML\n")
            self.log_to_console(f"2. Check video path: {abs_path}\n")
            self.log_to_console(f"3. In import dialog, use 'Relink Media' button\n")
            self.log_to_console(f"4. Select your video file manually\n")
            self.log_to_console(f"5. After import, if clips are offline:\n")
            self.log_to_console(f"   - Right-click timeline → Relink Selected Clips\n")
            self.log_to_console(f"   - Or: Media Pool → Right-click offline media → Relink\n")
            
            return {
                "status": "success",
                "message": f"TooBoooring Studio - FCP XML file exported successfully!\n\nFile: {xml_filename}\nLocation: {xml_path}",
                "file_path": str(xml_path)
            }
        
        except Exception as e:
            self.logger.error(f"FCP XML export failed: {e}", exc_info=True)
            self.log_to_console(f"FCP XML export failed: {str(e)}\n")
            return {"status": "error", "message": str(e)}
    
    def _frames_to_timecode(self, frames: int, fps: float) -> str:
        """Convert frame number to timecode string HH:MM:SS:FF (FF is always 2 digits)"""
        fps_int = int(round(fps))
        if fps_int <= 0:
            fps_int = 30
        hours = frames // (fps_int * 3600)
        minutes = (frames // (fps_int * 60)) % 60
        secs = (frames // fps_int) % 60
        frame_num = frames % fps_int
        # Ensure frame number is always 2 digits (0-29 for 30fps, 0-59 for 60fps, etc.)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frame_num:02d}"
    
    def get_waveform_data(self, file_path: str, width: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Extracts, downsamples, and returns waveform data.
        `width` is the pixel width of the canvas, so we can downsample to it.
        
        Uses caching to avoid re-extracting waveforms for the same file.
        
        Args:
            file_path: Path to video file
            width: Pixel width of canvas for downsampling
            
        Returns:
            List of waveform data or error dict
        """
        width_int = int(width)
        cache_key = f"{file_path}:{width_int}"
        
        # Check cache first
        if cache_key in self.waveform_cache:
            self.logger.debug(f"Using cached waveform for {file_path} at width {width_int}")
            return self.waveform_cache[cache_key]

        self.logger.info(f"Extracting waveform for {file_path}...")

        # Validate file path
        is_valid, error_msg = validate_video_path(file_path)
        if not is_valid:
            return self._error_response(error_msg)

        def status_callback(msg: str):
            self.logger.debug(f"CORE: {msg}")

        try:
            # 1. Extract full audio waveform using our existing core logic
            y = WaveformGenerator.extract_audio_waveform(
                file_path, 
                "", # ffmpeg_path
                status_callback
            )

            if y is None:
                self.logger.warning("No waveform data extracted")
                return None

            # 2. Downsample it to the exact width of our JS canvas
            downsampled_y = WaveformGenerator.downsample_waveform(y, width_int)

            # 3. Convert numpy array to a simple list for JSON
            waveform_list = downsampled_y.tolist()
            
            # 4. Cache the result
            self.waveform_cache[cache_key] = waveform_list
            self.logger.debug(f"Extracted and cached waveform with {len(waveform_list)} samples")
            
            return waveform_list

        except Exception as e:
            self.logger.error(f"Error extracting waveform: {e}", exc_info=True)
            return self._error_response(f"Error extracting waveform: {str(e)}")
    
    def get_waveforms_all_tracks(self, file_path: str, audio_tracks: List[Dict[str, Any]], 
                                 width: Union[int, str]) -> Dict[str, Any]:
        """
        Extracts waveforms for ALL audio tracks separately, downsamples them,
        and returns a dictionary mapping track indices to waveform data.
        
        Uses caching to avoid re-extracting waveforms for the same file.
        
        Args:
            file_path: Path to video file
            audio_tracks: List of audio track dictionaries with 'index', 'name', etc.
            width: Pixel width of the canvas for downsampling
            
        Returns:
            Dictionary: {track_index: {"waveform": [downsampled_data], "track_info": {...}}}
        """
        width_int = int(width)
        cache_key = f"{file_path}:{width_int}"
        
        # Check cache first
        if cache_key in self.multi_track_cache:
            self.logger.debug(f"Using cached multi-track waveforms for {file_path} at width {width_int}")
            return {"status": "success", "waveforms": self.multi_track_cache[cache_key]}
        
        self.logger.info(f"Extracting waveforms for all tracks in {file_path}...")
        
        # Validate file path
        is_valid, error_msg = validate_video_path(file_path)
        if not is_valid:
            return self._error_response(error_msg)
        
        def status_callback(msg: str):
            # Log at INFO level so we can see waveform extraction progress
            self.logger.info(f"Waveform: {msg.strip()}")
        
        try:
            # Prepare track info in the format expected by extract_audio_waveforms_all_tracks
            waveform_tracks = []
            for i, track in enumerate(audio_tracks):
                waveform_tracks.append({
                    "audio_index": i,
                    "stream_index": track.get("index", i),
                    "name": track.get("name", f"Track {i + 1}"),
                    "codec": track.get("codec", "unknown"),
                    "language": track.get("language", "")
                })
            
            # Log track information
            self.logger.info(f"Preparing to extract waveforms for {len(waveform_tracks)} track(s)")
            for track in waveform_tracks:
                self.logger.info(f"  Track {track['audio_index']}: stream_index={track['stream_index']}, name={track['name']}")
            
            # Extract waveforms for all tracks (if librosa is available)
            waveforms = WaveformGenerator.extract_audio_waveforms_all_tracks(
                file_path,
                "",  # ffmpeg_path (use system)
                waveform_tracks,
                status_callback
            )
            
            self.logger.info(f"Waveform extraction returned {len(waveforms) if waveforms else 0} waveforms")
            
            if not waveforms:
                # No waveforms extracted - log detailed info
                from video_production_app.utils.waveform import AUDIO_ANALYSIS_AVAILABLE
                self.logger.warning("No waveforms extracted (librosa may not be installed or extraction failed)")
                self.logger.info(f"  - AUDIO_ANALYSIS_AVAILABLE: {AUDIO_ANALYSIS_AVAILABLE}")
                self.logger.info(f"  - Number of tracks requested: {len(waveform_tracks)}")
                # Return empty result but still success (frontend handles empty waveforms)
                return {"status": "success", "waveforms": {}}
            
            # Downsample each waveform and convert to JSON-serializable format
            result = {}
            for track_index, waveform_data in waveforms.items():
                try:
                    waveform_array = waveform_data["waveform"]
                    track_info = waveform_data["track_info"]
                    
                    self.logger.info(f"Processing waveform for track {track_index}, shape: {waveform_array.shape if hasattr(waveform_array, 'shape') else 'unknown'}")
                    
                    # Downsample to canvas width
                    downsampled = WaveformGenerator.downsample_waveform(waveform_array, int(width))
                    
                    # Convert numpy array to list for JSON
                    waveform_list = downsampled.tolist()
                    self.logger.info(f"  Downsampled to {len(waveform_list)} points")
                    
                    result[track_index] = {
                        "waveform": waveform_list,
                        "track_info": track_info
                    }
                except Exception as e:
                    self.logger.error(f"Error processing waveform for track {track_index}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Successfully processed {len(result)} waveforms for frontend")
            
            # Cache the result
            self.multi_track_cache[cache_key] = result
            self.logger.debug(f"Cached multi-track waveforms for {file_path}")
            
            return {"status": "success", "waveforms": result}
            
        except Exception as e:
            self.logger.error(f"Error extracting waveforms: {e}", exc_info=True)
            return self._error_response(f"Error extracting waveforms: {str(e)}")
    
    def get_available_encoders(self) -> List[str]:
        """
        Returns a list of available encoders for the dropdown.
        
        Returns:
            List of encoder names
        """
        def status_callback(msg: str):
            self.logger.debug(f"CORE: {msg}")
        
        try:
            encoders = get_available_encoders("", status_callback)
            self.logger.info(f"Retrieved {len(encoders)} encoders")
            return encoders
        except Exception as e:
            self.logger.error(f"Error getting encoders: {e}", exc_info=True)
            return ["CPU (x264)"]  # Fallback
    
    def select_save_destination(self):
        """
        Opens a directory dialog to select save destination.
        """
        root = Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        save_path = filedialog.askdirectory(title="Select Save Folder")
        root.destroy()
        return save_path if save_path else None
    
    def analyze_all_tracks(self, video_path: str) -> Dict[str, Any]:
        """
        Analyzes all audio tracks in the video and returns detailed information.
        
        Args:
            video_path: Path to video file
            
        Returns:
            List of track analysis results or error dict
        """
        self.logger.info(f"Analyzing all tracks for {video_path}...")
        
        # Validate file path
        is_valid, error_msg = validate_video_path(video_path)
        if not is_valid:
            return self._error_response(error_msg)
        
        def status_callback(msg: str):
            self.logger.debug(f"CORE: {msg}")
        
        try:
            # Get audio tracks
            audio_tracks = get_audio_tracks(Path(video_path), "", status_callback)
            
            if not audio_tracks:
                return {"error": "No audio tracks found"}
            
            # Analyze each track
            results = []
            for track in audio_tracks:
                try:
                    analysis = analyze_audio_track_content(
                        Path(video_path),
                        track['index'],
                        ""
                    )
                    
                    # Combine track info with analysis
                    track_result = {
                        "index": track['index'],
                        "codec": track.get('codec', 'unknown'),
                        "channels": track.get('channel_str', '?'),
                        "sample_rate": track.get('sample_rate', '?'),
                        "bitrate": track.get('bitrate', 'N/A'),
                        "is_silent": analysis['is_silent'],
                        "mean_volume": analysis['mean_volume'],
                        "max_volume": analysis['max_volume'],
                        "status": analysis['status']
                    }
                    results.append(track_result)
                except Exception as e:
                    self.logger.error(f"Error analyzing track {track['index']}: {e}")
                    track_result = {
                        "index": track['index'],
                        "codec": track.get('codec', 'unknown'),
                        "channels": track.get('channel_str', '?'),
                        "sample_rate": track.get('sample_rate', '?'),
                        "bitrate": track.get('bitrate', 'N/A'),
                        "is_silent": True,
                        "mean_volume": None,
                        "max_volume": None,
                        "status": f"Error: {str(e)[:30]}"
                    }
                    results.append(track_result)
            
            self.logger.info(f"Analyzed {len(results)} tracks")
            return {"status": "success", "tracks": results}
            
        except Exception as e:
            self.logger.error(f"Error analyzing tracks: {e}", exc_info=True)
            return self._error_response(f"Error analyzing tracks: {str(e)}")

# --- Main Application ---
def main():
    api = Api() # Create the API

    ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web_ui')
    ui_dir = os.path.normpath(ui_dir)

    window = webview.create_window(
        'TooBoooring Studio 1.0',
        'file://' + os.path.join(ui_dir, 'index.html'),
        js_api=api,
        width=1280,
        height=800,
        min_size=(1000, 700)
    )

    api.window = window # Give the Api a reference to the window

    webview.start(debug=False)

if __name__ == '__main__':
    main()