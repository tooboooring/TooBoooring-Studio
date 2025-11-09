"""
Main processing tab for Video Production App.

This module contains the main processing tab functionality that matches exactly
the original Video_production_app_v3.py structure. It provides the same UI layout
and functionality as the original monolithic file.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable
import threading
from datetime import timedelta

from ..core.ffmpeg_wrapper import get_available_encoders, get_audio_tracks, analyze_audio_track_content
from ..core.video_processor import process_video_logic
from ..core.settings_manager import SettingsManager
from ..config import ENCODER_OPTIONS
from ..utils.colors import AppColors
from ..utils.helpers import format_time, validate_file_path


class MainTab:
    """
    Main processing tab for the Video Production App.
    
    This class replicates the exact UI structure and functionality from the
    original Video_production_app_v3.py file. It maintains the same layout,
    styling, and behavior as the original implementation.
    """
    
    def __init__(self, parent, settings: SettingsManager, 
                 ffmpeg_path: str = "", ffprobe_path: str = "",
                 on_state_update: Optional[Callable] = None):
        """
        Initialize the main processing tab.
        
        Args:
            parent: Parent widget for the tab
            settings: Settings manager instance
            ffmpeg_path: Path to FFmpeg executable
            ffprobe_path: Path to FFprobe executable
            on_state_update: Callback function called when state is updated
        """
        self.parent = parent
        self.settings = settings
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.on_state_update = on_state_update
        
        # State variables (matching original)
        self.video_path = ""
        self.save_path = ""
        self.available_tracks = []
        self.detected_segments = []
        self.processing = False
        
        # Set up the UI exactly as in original
        self.setup_ui()
    
    def setup_ui(self):
        """
        Set up the main processing tab user interface with scrollable content.
        
        This method creates a scrollable interface that can accommodate all
        the processing controls without cutting off content.
        """
        # Configure grid layout for scrollable content
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(0, weight=1)
        
        # Create main scrollable frame
        self.main_scrollable_frame = ctk.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
            scrollbar_button_color=AppColors.PRIMARY,
            scrollbar_button_hover_color=AppColors.PRIMARY_HOVER
        )
        self.main_scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # Create a centered container with max width for content
        content_frame = ctk.CTkFrame(self.main_scrollable_frame, fg_color="transparent")
        content_frame.grid(row=0, column=0, sticky="n")
        content_frame.configure(width=900)  # Max width for content
        
        # Video selection with enhanced styling (exactly as original)
        self.label_video = ctk.CTkLabel(
            content_frame, 
            text="No video file selected.", 
            anchor="w", 
            font=("Segoe UI", 11), 
            justify="left", 
            width=850,
            text_color=AppColors.TEXT_MUTED
        )
        self.button_video = ctk.CTkButton(
            content_frame, 
            text="📁  Select Video File", 
            command=self.select_video_file, 
            height=42, 
            font=("Segoe UI", 14, "bold"), 
            width=850,
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=10
        )
        
        # Save destination with enhanced styling (exactly as original)
        self.label_save = ctk.CTkLabel(
            content_frame, 
            text="No save destination selected.", 
            anchor="w", 
            font=("Segoe UI", 11), 
            justify="left", 
            width=850,
            text_color=AppColors.TEXT_MUTED
        )
        self.button_save = ctk.CTkButton(
            content_frame, 
            text="💾  Select Save Destination", 
            command=self.select_save_destination, 
            height=42, 
            font=("Segoe UI", 14, "bold"), 
            width=850,
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=10
        )
        
        # Audio track selection with enhanced styling (exactly as original)
        self.audio_track_var = ctk.StringVar(value="Select a video first...")
        self.label_audio_track = ctk.CTkLabel(
            content_frame, 
            text="🎧 Audio Track for Silence Detection:", 
            font=("Segoe UI", 13, "bold"), 
            width=850, 
            anchor="w",
            text_color=AppColors.TEXT_PRIMARY
        )
        self.option_audio_track = ctk.CTkOptionMenu(
            content_frame, 
            values=["Select a video first..."], 
            variable=self.audio_track_var, 
            state="disabled", 
            height=38, 
            width=850,
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=8,
            font=("Segoe UI", 12)
        )
        
        # Audio track information panel with enhanced styling (exactly as original)
        audio_info_frame = ctk.CTkFrame(
            content_frame, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER,
            width=850
        )
        audio_info_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            audio_info_frame, 
            text="🎵 Audio Track Details", 
            font=("Segoe UI", 13, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=0, column=0, padx=12, pady=(12, 8), sticky="w")
        
        # Button to analyze tracks with enhanced styling (exactly as original)
        self.button_analyze_tracks = ctk.CTkButton(
            audio_info_frame, 
            text="🔍 Analyze All Tracks", 
            command=self.analyze_all_tracks, 
            height=32, 
            width=160,
            fg_color=AppColors.INFO,
            hover_color=AppColors.PRIMARY_DARK,
            corner_radius=8,
            font=("Segoe UI", 11, "bold"),
            state="disabled"
        )
        self.button_analyze_tracks.grid(row=0, column=1, padx=12, pady=(12, 8), sticky="e")
        
        self.audio_info_textbox = ctk.CTkTextbox(
            audio_info_frame, 
            height=100, 
            font=("Consolas", 10), 
            fg_color=AppColors.BG_DARK,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=6,
            state="disabled"
        )
        self.audio_info_textbox.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")
        
        # Trim settings (exactly as original)
        trim_frame = ctk.CTkFrame(content_frame, fg_color="transparent", width=850)
        trim_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(trim_frame, text="Trim Start (seconds):", font=("", 11)).grid(row=0, column=0, sticky="w", padx=5)
        self.trim_start_entry = ctk.CTkEntry(trim_frame, placeholder_text="0")
        self.trim_start_entry.grid(row=1, column=0, sticky="ew", padx=5)
        
        ctk.CTkLabel(trim_frame, text="Trim End (seconds, optional):", font=("", 11)).grid(row=0, column=1, sticky="w", padx=5)
        self.trim_end_entry = ctk.CTkEntry(trim_frame, placeholder_text="Leave empty for full video")
        self.trim_end_entry.grid(row=1, column=1, sticky="ew", padx=5)
        
        # Encoder and format selection with enhanced styling (exactly as original)
        options_frame = ctk.CTkFrame(content_frame, fg_color="transparent", width=850)
        options_frame.grid_columnconfigure((0, 1), weight=1)
        
        encoder_frame = ctk.CTkFrame(
            options_frame, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER
        )
        encoder_frame.grid(row=0, column=0, sticky="ew", padx=5)
        ctk.CTkLabel(
            encoder_frame, 
            text="🎮 Video Encoder:", 
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).pack(pady=(12, 8))
        self.encoder_var = ctk.StringVar(value="Detecting...")
        self.option_encoder = ctk.CTkOptionMenu(
            encoder_frame, 
            values=["Detecting..."], 
            variable=self.encoder_var, 
            state="disabled", 
            height=36,
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=8,
            font=("Segoe UI", 11)
        )
        self.option_encoder.pack(padx=12, pady=(0, 12), fill="x")
        
        format_frame = ctk.CTkFrame(
            options_frame, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER
        )
        format_frame.grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkLabel(
            format_frame, 
            text="📺 Output Format:", 
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).pack(pady=(12, 8))
        self.format_var = ctk.StringVar(value="MP4")
        self.option_format = ctk.CTkOptionMenu(
            format_frame, 
            values=["MP4", "MKV"], 
            variable=self.format_var, 
            height=36,
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=8,
            font=("Segoe UI", 11)
        )
        self.option_format.pack(padx=12, pady=(0, 12), fill="x")
        
        # Preview button with enhanced styling (exactly as original)
        self.button_preview = ctk.CTkButton(
            content_frame, 
            text="👁  Preview Video", 
            command=self.preview_video, 
            height=40, 
            fg_color=AppColors.BG_LIGHT, 
            hover_color=AppColors.BG_CARD_HOVER,
            border_width=2,
            border_color=AppColors.BORDER,
            width=850,
            font=("Segoe UI", 13, "bold"),
            corner_radius=10
        )
        
        # Detect silence button with enhanced styling (exactly as original)
        self.button_detect = ctk.CTkButton(
            content_frame, 
            text="🔍  Detect Silence", 
            command=self.detect_silence_preview, 
            height=40, 
            fg_color=AppColors.INFO, 
            hover_color=AppColors.PRIMARY_DARK,
            width=850,
            font=("Segoe UI", 13, "bold"),
            corner_radius=10
        )
        
        # Timeline preview (using v1-style simple timeline) with enhanced styling (exactly as original)
        self.timeline = ctk.CTkFrame(
            content_frame, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER,
            height=100
        )
        self.timeline_label = ctk.CTkLabel(
            self.timeline, 
            text="📊 Click 'Detect Silence' to see timeline preview\n💡 Use Preview tab for interactive timeline with waveforms", 
            font=("Segoe UI", 11),
            text_color=AppColors.TEXT_MUTED
        )
        self.timeline_label.pack(expand=True)
        
        # Process button with progress - Enhanced styling (exactly as original)
        process_frame = ctk.CTkFrame(
            content_frame, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER,
            width=850
        )
        process_frame.grid_columnconfigure(0, weight=1)
        
        self.button_cut = ctk.CTkButton(
            process_frame, 
            text="✂️  Cut Silences & Export", 
            command=self.start_cutting_thread, 
            height=50, 
            font=("Segoe UI", 16, "bold"), 
            fg_color=AppColors.SUCCESS, 
            hover_color=AppColors.SUCCESS_HOVER,
            corner_radius=10
        )
        
        # Enhanced progress bar with better visibility
        progress_container = ctk.CTkFrame(
            process_frame,
            fg_color=AppColors.BG_DARK,
            corner_radius=8,
            border_width=2,
            border_color=AppColors.BORDER,
            height=60
        )
        progress_container.grid_columnconfigure(0, weight=1)
        
        # Progress percentage label (large, prominent)
        self.progress_percentage = ctk.CTkLabel(
            progress_container,
            text="0%",
            font=("Segoe UI", 24, "bold"),
            text_color=AppColors.SUCCESS,
            width=100
        )
        
        # Main progress bar (larger, more prominent)
        self.progress_bar = ctk.CTkProgressBar(
            progress_container, 
            height=32,
            corner_radius=8,
            border_width=2,
            border_color=AppColors.BORDER,
            progress_color=AppColors.SUCCESS,
            fg_color=AppColors.BG_LIGHT
        )
        self.progress_bar.set(0)
        
        # Detailed progress information
        self.progress_label = ctk.CTkLabel(
            progress_container, 
            text="⏹ Ready to process", 
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        )
        
        # ETA and speed information
        self.progress_details = ctk.CTkLabel(
            progress_container,
            text="",
            font=("Segoe UI", 10),
            text_color=AppColors.TEXT_SECONDARY
        )
        
        # Status textbox with enhanced styling (within scrollable frame)
        self.status_textbox = ctk.CTkTextbox(
            content_frame, 
            state="disabled", 
            fg_color=AppColors.BG_DARK, 
            font=("Consolas", 10), 
            corner_radius=10,
            border_width=1,
            border_color=AppColors.BORDER,
            height=150
        )
        
        # Add header with logo if available
        try:
            logo_path = Path(__file__).parent.parent.parent / "logo.png"
            if logo_path.exists():
                from PIL import Image, ImageTk
                import tkinter as tk
                
                # Create header frame
                header_frame = ctk.CTkFrame(
                    content_frame,
                    fg_color=AppColors.BG_CARD,
                    corner_radius=10,
                    border_width=1,
                    border_color=AppColors.BORDER,
                    height=80
                )
                
                # Load and resize logo
                logo_image = Image.open(logo_path)
                logo_image = logo_image.resize((60, 60), Image.Resampling.LANCZOS)
                logo_photo = ImageTk.PhotoImage(logo_image)
                
                # Logo label
                logo_label = tk.Label(
                    header_frame,
                    image=logo_photo,
                    bg=AppColors.BG_CARD
                )
                logo_label.image = logo_photo  # Keep a reference
                
                # App title
                title_label = ctk.CTkLabel(
                    header_frame,
                    text="🎬 Video Production Suite v3.0",
                    font=("Segoe UI", 20, "bold"),
                    text_color=AppColors.TEXT_PRIMARY
                )
                
                # Subtitle
                subtitle_label = ctk.CTkLabel(
                    header_frame,
                    text="Professional Silence Removal & Video Processing",
                    font=("Segoe UI", 12),
                    text_color=AppColors.TEXT_SECONDARY
                )
                
                # Layout header elements
                logo_label.pack(side="left", padx=15, pady=10)
                title_label.pack(side="left", padx=(10, 0), pady=(10, 0))
                subtitle_label.pack(side="left", padx=(10, 0), pady=(0, 10))
                
                print(f"✅ Added logo to main tab: {logo_path}")
        except Exception as e:
            print(f"⚠️ Could not add logo to main tab: {e}")
        
        # Layout exactly as original
        row = 0
        if 'header_frame' in locals():
            header_frame.grid(row=row, column=0, padx=15, pady=(10, 5), sticky="ew")
            row += 1
        
        self.button_video.grid(row=row, column=0, padx=15, pady=(10, 3), sticky="ew")
        row += 1
        self.label_video.grid(row=row, column=0, padx=15, pady=(0, 8), sticky="w")
        row += 1
        self.button_save.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        row += 1
        self.label_save.grid(row=row, column=0, padx=15, pady=(0, 8), sticky="w")
        row += 1
        self.label_audio_track.grid(row=row, column=0, padx=15, pady=(5, 2), sticky="w")
        row += 1
        self.option_audio_track.grid(row=row, column=0, padx=15, pady=(0, 3), sticky="ew")
        row += 1
        audio_info_frame.grid(row=row, column=0, padx=15, pady=(0, 5), sticky="ew")
        row += 1
        trim_frame.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        row += 1
        options_frame.grid(row=row, column=0, padx=15, pady=5, sticky="ew")
        row += 1
        self.button_preview.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        row += 1
        self.button_detect.grid(row=row, column=0, padx=15, pady=3, sticky="ew")
        row += 1
        self.timeline.grid(row=row, column=0, padx=15, pady=5, sticky="ew")
        row += 1
        process_frame.grid(row=row, column=0, padx=15, pady=8, sticky="ew")
        self.button_cut.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        
        # Layout the enhanced progress container
        progress_container.grid(row=1, column=0, sticky="ew", padx=12, pady=8)
        self.progress_percentage.grid(row=0, column=0, sticky="w", padx=15, pady=(8, 4))
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=15, pady=4)
        self.progress_label.grid(row=2, column=0, sticky="ew", padx=15, pady=(4, 2))
        self.progress_details.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 8))
        row += 1
        self.status_textbox.grid(row=row, column=0, padx=15, pady=(8, 15), sticky="ew")
        
        # Detect available encoders
        self._detect_encoders()
    
    def _detect_encoders(self):
        """
        Detect available video encoders.
        """
        def detect_callback(message):
            self.update_status(message)
        
        try:
            encoders = get_available_encoders(self.ffmpeg_path, detect_callback)
            self.option_encoder.configure(values=encoders, state="normal")
            if encoders:
                self.encoder_var.set(encoders[0])  # Set to first (usually "Automatic")
        except Exception as e:
            self.update_status(f"Error detecting encoders: {e}")
            self.option_encoder.configure(values=["CPU (x264)"], state="normal")
            self.encoder_var.set("CPU (x264)")
    
    def select_video_file(self):
        """
        Open file dialog to select a video file.
        """
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            # Validate file
            is_valid, error_msg = validate_file_path(file_path)
            if not is_valid:
                messagebox.showerror("Error", f"Invalid file: {error_msg}")
                return
            
            # Set video path
            self.video_path = file_path
            self.label_video.configure(text=Path(file_path).name)
            
            # Detect audio tracks
            self._detect_audio_tracks()
    
    def select_save_destination(self):
        """
        Open directory dialog to select save location.
        """
        directory = filedialog.askdirectory(title="Select Save Directory")
        
        if directory:
            self.save_path = directory
            self.label_save.configure(text=Path(directory).name)
    
    def _detect_audio_tracks(self):
        """
        Detect audio tracks in the selected video file.
        """
        if not self.video_path:
            return
        
        def status_callback(message):
            self.update_status(message)
        
        try:
            self.available_tracks = get_audio_tracks(
                Path(self.video_path), 
                self.ffprobe_path, 
                status_callback
            )
            
            if self.available_tracks:
                track_names = [f"Track {i+1}" for i in range(len(self.available_tracks))]
                self.option_audio_track.configure(values=track_names, state="normal")
                self.audio_track_var.set(track_names[0])
                self.button_analyze_tracks.configure(state="normal")
            else:
                self.option_audio_track.configure(values=["No audio tracks"], state="disabled")
                
        except Exception as e:
            self.update_status(f"Error detecting audio tracks: {e}")
            self.option_audio_track.configure(values=["Error detecting tracks"], state="disabled")
    
    def analyze_all_tracks(self):
        """
        Analyze all audio tracks for content and display detailed information.
        
        This method analyzes each audio track in the video to determine if it contains
        actual audio content or is silent. It displays the results in a formatted table
        showing track index, codec, channels, audio status, and volume levels.
        """
        if not self.video_path or not self.available_tracks:
            messagebox.showwarning("Warning", "Please select a video file first")
            return
        
        # Clear previous analysis results
        self.audio_info_textbox.configure(state="normal")
        self.audio_info_textbox.delete("1.0", "end")
        
        # Show header
        header = ("Track    Codec      Channels    Status         Mean Volume   Max Volume\n"
                 "─────────────────────────────────────────────────────────────────────\n")
        self.audio_info_textbox.insert("end", header)
        
        # Analyze each track
        for track in self.available_tracks:
            self.update_status(f"📊 Analyzing Track {track['index']}...")
            
            try:
                # Analyze the track content
                analysis = analyze_audio_track_content(
                    Path(self.video_path), 
                    track['index'], 
                    self.ffmpeg_path
                )
                
                # Store analysis results in track data
                track['analysis'] = analysis
                
                # Format volume values
                mean_str = f"{analysis['mean_volume']:.1f} dB" if analysis['mean_volume'] is not None else "N/A"
                max_str = f"{analysis['max_volume']:.1f} dB" if analysis['max_volume'] is not None else "N/A"
                
                # Add status icon based on analysis
                status_icon = ""
                if analysis['is_silent']:
                    status_icon = "🔇 "
                elif analysis['status'] == "Normal Audio":
                    status_icon = "🔊 "
                elif analysis['status'] == "Quiet Audio":
                    status_icon = "🔉 "
                elif analysis['status'] == "Loud Audio":
                    status_icon = "📢 "
                
                # Format the line with proper spacing
                line = (f"{track['index']:<8} "
                       f"{track['codec']:<10} "
                       f"{track['channel_str']:<10} "
                       f"{status_icon}{analysis['status']:<13} "
                       f"{mean_str:<12} "
                       f"{max_str:<10}\n")
                
                self.audio_info_textbox.insert("end", line)
                
            except Exception as e:
                # If analysis fails for a track, show error
                error_line = f"{track['index']:<8} {track['codec']:<10} {track['channel_str']:<10} ❌ Error: {str(e)[:20]}...\n"
                self.audio_info_textbox.insert("end", error_line)
                self.update_status(f"❌ Error analyzing Track {track['index']}: {e}")
        
        # Add completion message and legend
        self.audio_info_textbox.insert("end", "\n✅ Analysis complete!\n")
        self.audio_info_textbox.insert("end", "🔇 = Silent/Empty track | 🔉 = Quiet | 🔊 = Normal | 📢 = Loud\n")
        self.audio_info_textbox.configure(state="disabled")
        
        self.update_status("✅ Track analysis completed successfully")
    
    def preview_video(self):
        """
        Preview the selected video.
        """
        if not self.video_path:
            messagebox.showwarning("Warning", "Please select a video file first")
            return
        
        # This would implement the video preview functionality
        self.update_status("Video preview functionality would be implemented here")
    
    def detect_silence_preview(self):
        """
        Detect silence and show preview.
        """
        if not self.video_path:
            messagebox.showwarning("Warning", "Please select a video file first")
            return
        
        # This would implement the silence detection functionality
        self.update_status("Silence detection functionality would be implemented here")
    
    def start_cutting_thread(self):
        """
        Start video processing in a background thread with progress tracking.
        
        This method validates the input, starts the processing thread, and
        updates the UI to show processing state. The actual processing
        happens in run_silence_cutter() method.
        """
        if not self.video_path or not self.save_path:
            messagebox.showerror("Error", "Please select both video file and save directory")
            return
        
        if not self.available_tracks:
            messagebox.showerror("Error", "No audio tracks detected in video")
            return
        
        if not self.detected_segments:
            messagebox.showwarning("Warning", "No silence segments detected. Please run silence detection first.")
            return
        
        # Disable the button and show processing state
        self.button_cut.configure(state="disabled", text="⏳ Processing...")
        self.progress_bar.set(0)
        self.progress_percentage.configure(text="0%", text_color=AppColors.INFO)
        self.progress_label.configure(text="🚀 Starting video processing...")
        self.progress_details.configure(text="⏳ Initializing FFmpeg...")
        
        # Start processing in background thread
        thread = threading.Thread(target=self.run_silence_cutter, daemon=True)
        thread.start()
    
    def run_silence_cutter(self):
        """
        Main video processing logic with progress tracking.
        
        This method runs the actual video processing using FFmpeg,
        with real-time progress updates displayed in the UI.
        """
        try:
            # Get selected audio track index
            selected_track_name = self.audio_track_var.get()
            track_index = None
            for track in self.available_tracks:
                if track["name"] == selected_track_name:
                    track_index = track["index"]
                    break
            
            if track_index is None:
                self.update_status("❌ Error: Could not find selected track")
                return
            
            # Get trim settings
            trim_start = 0
            trim_end = None
            try:
                if self.trim_start_entry.get().strip():
                    trim_start = float(self.trim_start_entry.get())
                if self.trim_end_entry.get().strip():
                    trim_end = float(self.trim_end_entry.get())
            except ValueError:
                self.update_status("❌ Error: Invalid trim values")
                return
            
            # Get encoder settings
            encoder = self.encoder_var.get()
            video_params = ENCODER_OPTIONS.get(encoder, "-c:v libx264 -crf 23")
            
            # Get output format
            output_format = self.format_var.get().lower()
            
            # Get settings dictionary
            settings_dict = {
                "silence_db": self.settings.get("silence_db", -40),
                "silence_duration": self.settings.get("silence_duration", 0.7),
                "pad_before": self.settings.get("pad_before", 0.1),
                "pad_after": self.settings.get("pad_after", 0.0),
                "filter_length_threshold": self.settings.get("filter_length_threshold", 4096)
            }
            
            # Update status
            self.update_status("🚀 Starting video processing...")
            self.update_status(f"📁 Input: {Path(self.video_path).name}")
            self.update_status(f"📁 Output: {Path(self.save_path).name}")
            self.update_status(f"🎵 Track: {selected_track_name}")
            self.update_status(f"✂️ Segments: {len(self.detected_segments)}")
            
            # Run the actual processing with progress callback
            process_video_logic(
                video_path=self.video_path,
                output_dir=self.save_path,
                output_format=output_format,
                video_params=video_params,
                all_audio_tracks=self.available_tracks,
                silence_track_index=track_index,
                ffmpeg_path=self.ffmpeg_path,
                ffprobe_path=self.ffprobe_path,
                settings=settings_dict,
                status_callback=self.update_status,
                progress_callback=self.update_progress,
                trim_start=trim_start,
                trim_end=trim_end,
                segments=self.detected_segments
            )
            
            # Processing completed successfully
            self.progress_bar.set(1.0)
            self.progress_percentage.configure(text="100%", text_color=AppColors.SUCCESS)
            self.progress_label.configure(text="✅ Processing complete!")
            self.progress_details.configure(text="🎉 Video successfully exported!")
            self.update_status("🎉 Video processing completed successfully!")
            
        except Exception as e:
            # Handle any errors during processing
            self.update_status(f"❌ Processing failed: {e}")
            self.progress_percentage.configure(text="❌", text_color=AppColors.DANGER)
            self.progress_label.configure(text="❌ Processing failed")
            self.progress_details.configure(text=f"Error: {str(e)[:50]}...")
            
        finally:
            # Re-enable the button
            self.button_cut.configure(state="normal", text="✂️  Cut Silences & Export")
    
    def update_progress(self, percentage: float, eta: str, speed: float):
        """
        Update enhanced progress bar with processing information.
        
        This method is called by the video processing function to show
        real-time progress updates with a prominent progress bar and
        detailed information display.
        
        Args:
            percentage: Progress percentage (0-100)
            eta: Estimated time remaining (e.g., "0:02:30")
            speed: Processing speed multiplier (e.g., 2.5 for 2.5x real-time)
        """
        # Update large percentage display
        self.progress_percentage.configure(text=f"{percentage:.1f}%")
        
        # Update progress bar (convert percentage to 0-1 range)
        self.progress_bar.set(percentage / 100)
        
        # Update main progress label
        self.progress_label.configure(text="🔄 Processing video...")
        
        # Update detailed information
        self.progress_details.configure(
            text=f"⏱️ ETA: {eta} | 🚀 Speed: {speed:.2f}x | 📊 Processing audio/video"
        )
        
        # Change color based on progress
        if percentage < 25:
            color = AppColors.INFO
        elif percentage < 75:
            color = AppColors.WARNING
        else:
            color = AppColors.SUCCESS
            
        self.progress_percentage.configure(text_color=color)
        self.progress_bar.configure(progress_color=color)
    
    def update_status(self, message: str):
        """
        Update the status textbox with a message.
        
        Args:
            message: Status message to display
        """
        if self.status_textbox:
            self.status_textbox.configure(state="normal")
            self.status_textbox.insert("end", message + "\n")
            self.status_textbox.see("end")
            self.status_textbox.configure(state="disabled")
    
    def set_video_info(self, video_path: str, duration: float, audio_tracks: list):
        """
        Set video information from preview tab.
        
        This method is called when a video is loaded in the preview tab.
        It updates the main tab's state with the video information.
        
        Args:
            video_path: Path to the video file
            duration: Duration of the video in seconds
            audio_tracks: List of audio track information
        """
        # Update state
        self.video_path = video_path
        self.available_tracks = audio_tracks
        
        # Update UI elements
        self.label_video.configure(text=f"📁 {Path(video_path).name}")
        
        # Update audio track selector
        if audio_tracks:
            track_names = [track["name"] for track in audio_tracks]
            self.option_audio_track.configure(values=track_names, state="normal")
            self.audio_track_var.set(track_names[0])
            self.button_analyze_tracks.configure(state="normal")
        
        # Update status
        self.update_status(f"📁 Video loaded from preview: {Path(video_path).name}")
        self.update_status(f"⏱️ Duration: {format_time(duration)}")
        self.update_status(f"🎵 Audio tracks: {len(audio_tracks)}")
        
        # Notify app about state update
        if self.on_state_update:
            self.on_state_update(self.video_path, self.save_path, 
                               self.available_tracks, self.detected_segments)
    
    def set_detected_segments(self, segments: list, track_index: int):
        """
        Set detected segments from preview tab.
        
        This method is called when silence detection is completed in the preview tab.
        It updates the main tab's state with the detected segments.
        
        Args:
            segments: List of detected silence segments
            track_index: Index of the track that was analyzed
        """
        # Update state
        self.detected_segments = segments
        
        # Update status
        self.update_status(f"🔍 Silence detection completed from preview tab")
        self.update_status(f"📊 Detected {len(segments)} segments on track {track_index + 1}")
        
        # Calculate and display statistics
        if segments:
            total_audible = sum(end - start for start, end in segments)
            self.update_status(f"✅ Audible segments: {format_time(total_audible)}")
            self.update_status(f"📊 Total segments: {len(segments)}")
        
        # Notify app about state update
        if self.on_state_update:
            self.on_state_update(self.video_path, self.save_path, 
                               self.available_tracks, self.detected_segments)