import webview
import os
import sys
from tkinter import Tk, filedialog
from pathlib import Path

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
    from video_production_app.config import ENCODER_OPTIONS
    import numpy as np
else:
        # Use relative imports when run as a module
        from .core.ffmpeg_wrapper import get_video_duration, get_audio_tracks, get_available_encoders, analyze_audio_track_content
        from .core.silence_detector import detect_silence, parse_segments
        from .core.settings_manager import SettingsManager
        from .core.video_processor import process_video_logic
        from .ui.widgets.waveform import WaveformGenerator
        from .config import ENCODER_OPTIONS
        import numpy as np

# This is the "bridge" for JS to call Python
class Api:
    def __init__(self):
        self.settings = SettingsManager() # Assumes default config file
        self.window = None # We'll set this from main
        self.console_log = [] # To store logs
        self.available_encoders = [] # Store available encoders
    
    def say_hello(self, name):
        print(f"Hello from {name}!")
        return f"Hello, {name}! Python says hi."
    
    def log_to_console(self, message):
        """Sends a log message to the web UI console."""
        print(message) # Also print to terminal
        self.console_log.append(message)
        if self.window:
            # Call a *JavaScript* function from Python
            # Escape quotes and newlines for JavaScript
            escaped_message = message.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
            try:
                self.window.evaluate_js(f'window.app.addLog("{escaped_message}");')
            except Exception as e:
                print(f"Error sending log to console: {e}")
    
    def get_app_config(self):
        """Called by JS on load to get encoders and settings."""
        # Check FFmpeg/FFprobe availability first
        def status_cb(msg): 
            print(msg) # Print to terminal
            # Also send to web console if window is available
            if self.window:
                try:
                    escaped_msg = msg.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                    self.window.evaluate_js(f'window.app.addLog("{escaped_msg}");')
                except:
                    pass
        
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
            # Use the actual path from your app config if available
            print("Python: Starting encoder detection...")
            print(f"Python: ENCODER_OPTIONS keys: {list(ENCODER_OPTIONS.keys())}")
            encoders = get_available_encoders("", status_cb)
            print(f"Python: get_available_encoders returned {len(encoders)} encoders")
            print(f"Python: Encoder list: {encoders}")
            for i, enc in enumerate(encoders):
                print(f"  [{i}] {enc}")
            status_cb(f"📊 Encoder detection complete. Found {len(encoders)} option(s).\n")
        except Exception as e:
            print(f"Could not get encoders: {e}")
            status_cb(f"❌ Error detecting encoders: {str(e)}\n")
            import traceback
            traceback.print_exc()
        
        # Save encoders for use in export_video
        self.available_encoders = encoders
        print(f"Python: self.available_encoders = {self.available_encoders}")
        
        result = {
            "encoders": encoders,
            "settings": self.settings.settings
        }
        print(f"Python: Returning config with {len(encoders)} encoders")
        print(f"Python: result['encoders'] = {result['encoders']}")
        print(f"Python: result type: {type(result)}")
        print(f"Python: result['encoders'] type: {type(result['encoders'])}")
        if isinstance(result['encoders'], list):
            print(f"Python: result['encoders'] length: {len(result['encoders'])}")
        return result
    
    def load_video(self):
        root = Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)

        file_path = filedialog.askopenfilename(
            title="Select a Video File",
            filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi"), ("All Files", "*.*")]
        )
        root.destroy()

        if not file_path:
            return None

        print(f"Python: Analyzing {file_path}...")

        # Use console logger
        status_callback = self.log_to_console

        try:
            # Get info from our core Python files
            duration = get_video_duration(Path(file_path), "", status_callback)
            audio_tracks = get_audio_tracks(Path(file_path), "", status_callback)

            video_info = {
                "filePath": file_path,
                "fileName": Path(file_path).name,
                "duration": duration,
                "audioTracks": audio_tracks
            }

            # Return the whole dictionary to JavaScript
            return video_info

        except Exception as e:
            print(f"Error analyzing video: {e}")
            return {"error": str(e)}
    
    def detect_silence(self, video_path, track_index):
        print(f"Python: Detecting silence for {video_path} on track {track_index}")

        # Use console logger
        status_callback = self.log_to_console

        try:
            settings_dict = self.settings.settings # Get all current settings

            # 1. Detect
            ffmpeg_log = detect_silence(
                Path(video_path),
                track_index,
                "", # ffmpeg_path (use system)
                settings_dict,
                status_callback
            )

            # 2. Parse
            duration = get_video_duration(Path(video_path), "", status_callback)
            segments = parse_segments(
                ffmpeg_log,
                duration,
                settings_dict,
                status_callback
            )

            print(f"Python: Found {len(segments)} segments.")
            return segments

        except Exception as e:
            print(f"Error detecting silence: {e}")
            return {"error": str(e)}
    
    def get_loadable_file_url(self, file_path):
        """
        Returns a URL that the pywebview window can use to load a local file.
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
            print(f"Error creating file URL: {e}")
            return None
    
    def export_video(self, video_info, segments, export_settings):
        """
        Receives the video info, segments, and export settings from JavaScript
        and starts the ffmpeg export process.
        """
        print("Python: Received request to export video.")

        # 1. Get save location if not provided in settings
        save_path = export_settings.get('save_path')
        if not save_path:
            save_path = self.select_save_destination()
            if not save_path:
                print("Python: Export cancelled by user (no save folder).")
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

            print("Python: Export complete!")
            return {"status": "success", "message": f"Export complete! Saved to {save_path}"}

        except Exception as e:
            print(f"Python: Export failed: {e}")
            self.log_to_console(f"Export failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_waveform_data(self, file_path, width):
        """
        Extracts, downsamples, and returns waveform data.
        `width` is the pixel width of the canvas, so we can downsample to it.
        """
        print(f"Python: Extracting waveform for {file_path}...")

        def status_callback(msg):
            print(f"CORE: {msg}")

        try:
            # 1. Extract full audio waveform using our existing core logic
            y = WaveformGenerator.extract_audio_waveform(
                file_path, 
                "", # ffmpeg_path
                status_callback
            )

            if y is None:
                return None

            # 2. Downsample it to the exact width of our JS canvas
            downsampled_y = WaveformGenerator.downsample_waveform(y, int(width))

            # 3. Convert numpy array to a simple list for JSON
            return downsampled_y.tolist()

        except Exception as e:
            print(f"Error extracting waveform: {e}")
            return {"error": str(e)}
    
    def get_waveforms_all_tracks(self, file_path, audio_tracks, width):
        """
        Extracts waveforms for ALL audio tracks separately, downsamples them,
        and returns a dictionary mapping track indices to waveform data.
        
        Args:
            file_path: Path to video file
            audio_tracks: List of audio track dictionaries with 'index', 'name', etc.
            width: Pixel width of the canvas for downsampling
            
        Returns:
            Dictionary: {track_index: {"waveform": [downsampled_data], "track_info": {...}}}
        """
        print(f"Python: Extracting waveforms for all tracks in {file_path}...")
        
        def status_callback(msg):
            print(f"CORE: {msg}")
        
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
                return {"error": "No waveforms extracted"}
            
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
            
            print(f"Python: Extracted {len(result)} waveforms")
            return result
            
        except Exception as e:
            print(f"Error extracting waveforms: {e}")
            return {"error": str(e)}
    
    def get_available_encoders(self):
        """
        Returns a list of available encoders for the dropdown.
        """
        def status_callback(msg):
            print(f"CORE: {msg}")
        
        try:
            encoders = get_available_encoders("", status_callback)
            return encoders
        except Exception as e:
            print(f"Error getting encoders: {e}")
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
    
    def analyze_all_tracks(self, video_path):
        """
        Analyzes all audio tracks in the video and returns detailed information.
        """
        print(f"Python: Analyzing all tracks for {video_path}...")
        
        def status_callback(msg):
            print(f"CORE: {msg}")
        
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
                    print(f"Error analyzing track {track['index']}: {e}")
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
            
            return results
            
        except Exception as e:
            print(f"Error analyzing tracks: {e}")
            return {"error": str(e)}

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