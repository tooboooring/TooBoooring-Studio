"""
Frame preview widget for Video Production App.

This module provides a frame preview widget that displays individual video frames
at specific timestamps. It includes navigation controls, audio track selection,
and integration with FFplay for external playback.

Key features:
- Frame extraction and display using OpenCV
- Time-based navigation controls
- Audio track detection and selection
- External playback with FFplay
- Multi-track audio mixing

The FramePreview widget is used in the preview tab to allow users to
scrub through video frames and preview content before processing.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import timedelta
from typing import Optional, List, Dict, Any

import customtkinter as ctk
from tkinter import Canvas, messagebox
from PIL import Image, ImageTk

# Check for optional OpenCV package
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("[WARNING] opencv-python not installed. Frame preview will be limited.")


class FramePreview(ctk.CTkFrame):
    """
    Simple frame preview widget that shows single frames at a time.
    
    This widget provides a video frame preview with navigation controls,
    audio track selection, and external playback capabilities. It uses
    OpenCV for frame extraction and FFplay for external playback.
    
    Key features:
    - Frame-by-frame navigation
    - Time-based jumping (forward/backward)
    - Audio track detection and selection
    - External playback with FFplay
    - Multi-track audio mixing
    
    Attributes:
        video_path: Path to currently loaded video file
        cap: OpenCV VideoCapture object
        current_time: Current playback time in seconds
        duration: Total video duration in seconds
        fps: Video frame rate
        audio_tracks: List of detected audio tracks
        selected_audio_track: Index of currently selected audio track
        
    Example usage:
        preview = FramePreview(parent_frame)
        preview.load_video("video.mp4", "")
        preview.show_frame_at_time(30.5)  # Show frame at 30.5 seconds
    """
    
    def __init__(self, master, **kwargs):
        """
        Initialize the frame preview widget.
        
        Args:
            master: Parent widget
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, **kwargs)
        
        # Video-related attributes
        self.video_path = None
        self.cap = None
        self.current_time = 0
        self.duration = 0
        self.fps = 30
        
        # Audio track information
        self.audio_tracks = []  # List of audio tracks
        self.selected_audio_track = 0  # Selected track index
        
        # Set up the user interface
        self.setup_ui()
    
    def setup_ui(self):
        """
        Set up the frame preview user interface.
        
        This method creates all the UI elements including the preview canvas,
        navigation buttons, time display, audio track selector, and play button.
        """
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Preview canvas for displaying video frames
        self.canvas = Canvas(
            self, 
            bg="black", 
            highlightthickness=0, 
            width=640, 
            height=360
        )
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Placeholder text when no video is loaded
        self.placeholder = self.canvas.create_text(
            320, 180, 
            text="No frame loaded\nClick timeline to preview",
            fill="gray", 
            font=("Arial", 14), 
            justify="center"
        )
        
        # Control buttons frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, pady=(0, 10))
        
        # Navigation buttons
        ctk.CTkButton(
            btn_frame, 
            text="⏮ -1s", 
            width=70, 
            command=lambda: self.jump_relative(-1),
            font=("", 12)
        ).pack(side="left", padx=3)
        
        ctk.CTkButton(
            btn_frame, 
            text="◀ -0.1s", 
            width=70, 
            command=lambda: self.jump_relative(-0.1),
            font=("", 10)
        ).pack(side="left", padx=3)
        
        # Time display label
        self.time_label = ctk.CTkLabel(
            btn_frame, 
            text="00:00.00", 
            font=("", 13, "bold")
        )
        self.time_label.pack(side="left", padx=15)
        
        ctk.CTkButton(
            btn_frame, 
            text="▶ +0.1s", 
            width=70, 
            command=lambda: self.jump_relative(0.1),
            font=("", 10)
        ).pack(side="left", padx=3)
        
        ctk.CTkButton(
            btn_frame, 
            text="⏭ +1s", 
            width=70, 
            command=lambda: self.jump_relative(1),
            font=("", 12)
        ).pack(side="left", padx=3)
        
        # Audio track selector frame
        audio_track_frame = ctk.CTkFrame(self, fg_color="gray30", corner_radius=5)
        audio_track_frame.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="ew")
        
        ctk.CTkLabel(
            audio_track_frame, 
            text="🎵 Audio Track:",
            font=("", 11, "bold")
        ).pack(side="left", padx=10)
        
        # Audio track selection dropdown
        self.audio_track_var = ctk.StringVar(value="No tracks detected")
        self.audio_track_menu = ctk.CTkOptionMenu(
            audio_track_frame, 
            values=["No tracks detected"],
            variable=self.audio_track_var,
            command=self.on_audio_track_change,
            width=300
        )
        self.audio_track_menu.pack(side="left", padx=10, pady=5, fill="x", expand=True)
        
        # External play button
        self.btn_play = ctk.CTkButton(
            self, 
            text="▶ Play in FFplay", 
            command=self.play_external, 
            height=35,
            fg_color="#2fb344", 
            hover_color="#25a339"
        )
        self.btn_play.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
    
    def load_video(self, video_path: str, ffprobe_path: str = "") -> bool:
        """
        Load video for frame extraction and detect audio tracks.
        
        This method opens a video file using OpenCV and detects all audio
        tracks using FFprobe. It sets up the video capture object and
        displays the first frame.
        
        Args:
            video_path: Path to the video file to load
            ffprobe_path: Path to FFprobe executable (empty string uses system PATH)
            
        Returns:
            True if video loaded successfully, False otherwise
            
        Example:
            success = preview.load_video("video.mp4", "")
            if success:
                print("Video loaded successfully")
        """
        # Check if OpenCV is available
        if not CV2_AVAILABLE:
            return False
        
        try:
            # Release any existing video capture
            if self.cap:
                self.cap.release()
            
            # Set video path and open with OpenCV
            self.video_path = video_path
            self.cap = cv2.VideoCapture(video_path)
            
            # Check if video opened successfully
            if not self.cap.isOpened():
                return False
            
            # Get video properties
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.duration = total_frames / self.fps if self.fps > 0 else 0
            
            # Detect audio tracks in the video
            self.detect_audio_tracks(video_path, ffprobe_path)
            
            # Show first frame
            self.show_frame_at_time(0)
            
            return True
            
        except Exception:
            return False
    
    def detect_audio_tracks(self, video_path: str, ffprobe_path: str = ""):
        """
        Detect all audio tracks in the video using FFprobe.
        
        This method runs FFprobe to analyze the video file and extract
        information about all audio tracks, including codec, channels,
        sample rate, and language.
        
        Args:
            video_path: Path to the video file
            ffprobe_path: Path to FFprobe executable (empty string uses system PATH)
            
        Example:
            preview.detect_audio_tracks("video.mp4", "")
            # Updates self.audio_tracks with track information
        """
        try:
            # Use provided path or default to system PATH
            ffprobe = ffprobe_path or "ffprobe"
            
            # Build FFprobe command to get audio stream information
            cmd = [
                str(ffprobe), 
                "-v", "error",  # Only show errors
                "-show_streams",  # Show stream information
                "-select_streams", "a",  # Only audio streams
                "-of", "json",  # JSON output format
                video_path
            ]
            
            # Set up Windows-specific startup info
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Run FFprobe command
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                encoding='utf-8', 
                errors='ignore', 
                startupinfo=startupinfo
            )
            
            # Parse JSON output
            streams = json.loads(result.stdout).get("streams", [])
            self.audio_tracks = []
            
            # Process each audio stream
            for i, stream in enumerate(streams):
                track_index = stream.get("index", i)
                codec = stream.get("codec_name", "unknown")
                channels = stream.get("channels", "?")
                sample_rate = stream.get("sample_rate", "?")
                language = stream.get("tags", {}).get("language", "und")
                
                # Format channel information
                if channels == 1:
                    ch_str = "mono"
                elif channels == 2:
                    ch_str = "stereo"
                else:
                    ch_str = f"{channels}ch"
                
                # Format sample rate
                try:
                    sr_khz = int(sample_rate) // 1000
                    sr_str = f"{sr_khz}kHz"
                except (ValueError, TypeError):
                    sr_str = "?"
                
                # Create display name
                display_name = f"Track {i+1} (Stream {track_index}): {codec}, {ch_str}, {sr_str}"
                if language != "und":
                    display_name += f", {language}"
                
                # Store track information
                self.audio_tracks.append({
                    "stream_index": track_index,
                    "audio_index": i,
                    "display_name": display_name,
                    "codec": codec,
                    "language": language
                })
            
            # Update UI with detected tracks
            if self.audio_tracks:
                track_names = [t["display_name"] for t in self.audio_tracks]
                self.audio_track_menu.configure(values=track_names)
                self.audio_track_var.set(track_names[0])
                self.selected_audio_track = 0
            else:
                self.audio_track_menu.configure(values=["No audio tracks found"])
                self.audio_track_var.set("No audio tracks found")
                
        except Exception as e:
            print(f"Error detecting audio tracks: {e}")
            self.audio_tracks = []
    
    def on_audio_track_change(self, selected_name: str):
        """
        Handle audio track selection change.
        
        This method is called when the user selects a different audio track
        from the dropdown menu. It updates the selected track index.
        
        Args:
            selected_name: Display name of the selected track
            
        Example:
            preview.on_audio_track_change("Track 1 (Stream 0): aac, stereo, 48kHz")
        """
        # Find the track with the matching display name
        for i, track in enumerate(self.audio_tracks):
            if track["display_name"] == selected_name:
                self.selected_audio_track = i
                break
    
    def show_frame_at_time(self, time_seconds: float):
        """
        Extract and display frame at specific time.
        
        This method seeks to a specific time in the video and displays
        the corresponding frame in the preview canvas. It handles frame
        extraction, resizing, and display.
        
        Args:
            time_seconds: Time in seconds to seek to
            
        Example:
            preview.show_frame_at_time(30.5)  # Show frame at 30.5 seconds
        """
        # Check if video is loaded
        if not self.cap or not self.cap.isOpened():
            return
        
        try:
            # Clamp time to valid range
            self.current_time = max(0, min(time_seconds, self.duration))
            
            # Calculate frame number
            frame_number = int(self.current_time * self.fps)
            
            # Seek to the frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = self.cap.read()
            
            if ret:
                # Convert BGR to RGB for display
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Get canvas dimensions
                canvas_width = self.canvas.winfo_width() or 640
                canvas_height = self.canvas.winfo_height() or 360
                
                # Calculate scaling to fit canvas
                frame_height, frame_width = frame_rgb.shape[:2]
                scale = min(canvas_width / frame_width, canvas_height / frame_height)
                new_width = int(frame_width * scale)
                new_height = int(frame_height * scale)
                
                # Resize frame to fit canvas
                frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
                
                # Convert to PIL Image and then to PhotoImage
                img = Image.fromarray(frame_resized)
                self.photo = ImageTk.PhotoImage(image=img)
                
                # Clear canvas and display new frame
                self.canvas.delete("all")
                self.canvas.create_image(
                    canvas_width // 2, 
                    canvas_height // 2,
                    image=self.photo, 
                    anchor="center"
                )
                
                # Update time label
                time_str = str(timedelta(seconds=self.current_time))[:10]
                self.time_label.configure(text=time_str)
                
        except Exception as e:
            print(f"Error showing frame: {e}")
    
    def jump_relative(self, seconds: float):
        """
        Jump forward or backward by specified seconds.
        
        This method moves the current playback position by a specified
        amount of time and displays the corresponding frame.
        
        Args:
            seconds: Number of seconds to jump (positive = forward, negative = backward)
            
        Example:
            preview.jump_relative(1.0)   # Jump forward 1 second
            preview.jump_relative(-0.5)  # Jump backward 0.5 seconds
        """
        if self.video_path:
            new_time = self.current_time + seconds
            self.show_frame_at_time(new_time)
    
    def play_external(self):
        """
        Launch FFplay with ALL audio tracks mixed together.
        
        This method opens the video in FFplay for external playback.
        If multiple audio tracks are present, it mixes them together
        using FFmpeg before piping to FFplay.
        
        Example:
            preview.play_external()  # Opens video in FFplay
        """
        # Check if video is loaded
        if not self.video_path:
            messagebox.showwarning("Warning", "No video loaded!")
            return
        
        # Find FFmpeg and FFplay executables (now in bin/ folder)
        base_path = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent.parent
        bin_path = base_path / "bin"
        ffplay_path = bin_path / "ffplay.exe"
        ffmpeg_path = bin_path / "ffmpeg.exe"
        
        # Fall back to system PATH if not found
        if not ffplay_path.exists():
            ffplay_path = "ffplay"
        if not ffmpeg_path.exists():
            ffmpeg_path = "ffmpeg"
        
        try:
            num_audio_tracks = len(self.audio_tracks)
            
            if num_audio_tracks <= 1:
                # Only one track, play normally
                cmd = [str(ffplay_path), "-ss", str(self.current_time), "-autoexit", self.video_path]
                subprocess.Popen(cmd)
            else:
                # Multiple tracks - mix them together
                # Build audio mix filter: [0:a:0][0:a:1]amix=inputs=2:duration=longest
                audio_inputs = "".join([f"[0:a:{i}]" for i in range(num_audio_tracks)])
                mix_filter = f"{audio_inputs}amix=inputs={num_audio_tracks}:duration=longest:dropout_transition=0[aout]"
                
                # FFmpeg command: mix audio and output to pipe
                ffmpeg_cmd = [
                    str(ffmpeg_path),
                    "-ss", str(self.current_time),  # Start from current time
                    "-i", self.video_path,  # Input video
                    "-filter_complex", f"{mix_filter}",  # Audio mixing filter
                    "-map", "0:v:0",  # Map video stream
                    "-map", "[aout]",  # Map mixed audio
                    "-c:v", "copy",  # Copy video codec
                    "-c:a", "aac",  # Encode audio as AAC
                    "-f", "matroska",  # Use matroska container for piping
                    "pipe:1"  # Output to stdout
                ]
                
                # FFplay command: read from stdin
                ffplay_cmd = [str(ffplay_path), "-autoexit", "-"]
                
                # Set up Windows-specific startup info
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                # Create pipe: ffmpeg -> ffplay
                ffmpeg_proc = subprocess.Popen(
                    ffmpeg_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.DEVNULL, 
                    startupinfo=startupinfo
                )
                ffplay_proc = subprocess.Popen(
                    ffplay_cmd, 
                    stdin=ffmpeg_proc.stdout, 
                    startupinfo=startupinfo
                )
                
                # Allow ffmpeg to receive SIGPIPE if ffplay exits
                if ffmpeg_proc.stdout:
                    ffmpeg_proc.stdout.close()
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not launch ffplay: {e}")
    
    def cleanup(self):
        """
        Clean up resources when widget is destroyed.
        
        This method releases the OpenCV video capture object to free
        up system resources.
        
        Example:
            preview.cleanup()  # Call when closing the application
        """
        if self.cap:
            self.cap.release()
