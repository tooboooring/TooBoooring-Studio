import webview
import os
import sys
import time
from tkinter import Tk, filedialog
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

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
    from video_production_app.ui.widgets.waveform import WaveformGenerator
    from video_production_app.config import ENCODER_OPTIONS, UI_SETTINGS
    from video_production_app.utils.logger import app_logger
    from video_production_app.utils.validators import validate_video_path, validate_track_index, validate_trim_values
    import numpy as np
else:
        # Use relative imports when run as a module
        from .core.ffmpeg_wrapper import get_video_duration, get_audio_tracks, get_available_encoders, analyze_audio_track_content
        from .core.silence_detector import detect_silence, parse_segments
        from .core.settings_manager import SettingsManager
        from .core.video_processor import process_video_logic
        from .ui.widgets.waveform import WaveformGenerator
        from .config import ENCODER_OPTIONS, UI_SETTINGS
        from .utils.logger import app_logger
        from .utils.validators import validate_video_path, validate_track_index, validate_trim_values
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
            self.logger.error(f"Error analyzing video: {e}", exc_info=True)
            return self._error_response(f"Error analyzing video: {str(e)}")
    
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
                return temp_file
            else:
                self.logger.error(f"FFmpeg failed: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating video with audio tracks: {e}", exc_info=True)
            return None
    
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
            if self.window:
                try:
                    self.window.evaluate_js(f"window.updateProgress({percentage}, '{eta}', {speed});")
                except:
                    pass  # Ignore errors if JS function doesn't exist yet

        try:
            # 6. Call our existing core function!
            process_video_logic(
                video_path=video_info['filePath'],
                output_dir=save_path,
                output_format=output_format,
                video_params=video_params,
                all_audio_tracks=video_info['audioTracks'],
                silence_track_index=video_info['audioTracks'][0]['index'], # Just use first track for now
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
            return {"status": "success", "message": f"Export complete! Saved to {save_path}"}

        except Exception as e:
            self.logger.error(f"Export failed: {e}", exc_info=True)
            self.log_to_console(f"Export failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
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
            self.logger.debug(f"CORE: {msg}")
        
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
            
            # Extract waveforms for all tracks
            waveforms = WaveformGenerator.extract_audio_waveforms_all_tracks(
                file_path,
                "",  # ffmpeg_path (use system)
                waveform_tracks,
                status_callback
            )
            
            if not waveforms:
                return self._error_response("No waveforms extracted")
            
            # Downsample each waveform and convert to JSON-serializable format
            result = {}
            for track_index, waveform_data in waveforms.items():
                waveform_array = waveform_data["waveform"]
                track_info = waveform_data["track_info"]
                
                # Downsample to canvas width
                downsampled = WaveformGenerator.downsample_waveform(waveform_array, int(width))
                
                # Convert numpy array to list for JSON
                result[track_index] = {
                    "waveform": downsampled.tolist(),
                    "track_info": track_info
                }
            
            self.logger.info(f"Extracted {len(result)} waveforms")
            
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

    ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web_ui')
    ui_dir = os.path.normpath(ui_dir)

    window = webview.create_window(
        'Video Production Suite v4.0',
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