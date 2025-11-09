"""
Preview and Analysis tab for Video Production App.

This module contains the preview tab functionality that matches exactly
the original Video_production_app_v3.py structure. It provides the same UI layout
and functionality as the original monolithic file.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable
import threading

from ..core.ffmpeg_wrapper import get_audio_tracks, get_video_duration, get_available_encoders, analyze_audio_track_content
from ..core.silence_detector import detect_silence, parse_segments
from ..core.video_processor import process_video_logic
from ..core.settings_manager import SettingsManager
from .widgets.frame_preview import FramePreview
from .widgets.timeline import InteractiveTimeline
from .widgets.waveform import WaveformGenerator
from ..utils.colors import AppColors
from ..utils.helpers import format_time
from ..config import ENCODER_OPTIONS


class PreviewTab:
    """
    Preview and Analysis tab for the Video Production App.
    
    This class replicates the exact UI structure and functionality from the
    original Video_production_app_v3.py file. It maintains the same layout,
    styling, and behavior as the original implementation.
    """
    
    def __init__(self, parent, settings: SettingsManager, 
                 ffmpeg_path: str = "", ffprobe_path: str = "", ffplay_path: str = "",
                 on_video_loaded: Optional[Callable] = None, 
                 on_silence_detected: Optional[Callable] = None):
        """
        Initialize the preview tab.
        
        Args:
            parent: Parent widget for the tab
            settings: Settings manager instance
            ffmpeg_path: Path to FFmpeg executable
            ffprobe_path: Path to FFprobe executable
            ffplay_path: Path to FFplay executable
            on_video_loaded: Callback function called when video is loaded
            on_silence_detected: Callback function called when silence detection completes
        """
        self.parent = parent
        self.settings = settings
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.ffplay_path = ffplay_path
        self.on_video_loaded = on_video_loaded
        self.on_silence_detected = on_silence_detected
        
        # State variables (matching original)
        self.video_path = ""
        self.audio_tracks = []
        self.available_tracks = []  # For audio analysis
        self.detected_segments = []
        self.duration = 0
        self.save_path = ""  # Save destination for export
        self.available_encoders = []  # List of available encoders
        
        # Set up the UI exactly as in original
        self.setup_ui()
    
    def setup_ui(self):
        """
        Set up the preview tab user interface.
        
        This method replicates the exact UI structure from the original
        Video_production_app_v3.py file.
        """
        # Configure grid layout exactly as original
        self.parent.grid_columnconfigure(0, weight=3)
        self.parent.grid_columnconfigure(1, weight=2)
        self.parent.grid_rowconfigure(1, weight=1)
        
        # Header with controls - Enhanced styling (exactly as original)
        header_frame = ctk.CTkFrame(
            self.parent, 
            fg_color=AppColors.BG_CARD, 
            corner_radius=12,
            border_width=1,
            border_color=AppColors.BORDER,
            height=110
        )
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=12)
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_propagate(False)
        
        # Title with gradient effect (using bold font and primary color) (exactly as original)
        title_label = ctk.CTkLabel(
            header_frame, 
            text="🎬 Smart Preview & Analysis", 
            font=("Segoe UI", 20, "bold"),
            text_color=AppColors.PRIMARY
        )
        title_label.grid(row=0, column=0, padx=20, pady=(12, 5), sticky="w")
        
        # Control buttons with enhanced styling (exactly as original)
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=20, pady=10, sticky="e")
        
        load_btn = ctk.CTkButton(
            btn_frame, 
            text="📁 Load Video", 
            command=self.preview_load_video,
            height=38, 
            width=130, 
            font=("Segoe UI", 13, "bold"),
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=8
        )
        load_btn.pack(side="left", padx=5)
        
        # Track selector for silence detection with improved styling (exactly as original)
        ctk.CTkLabel(
            btn_frame, 
            text="Detect silence in:", 
            font=("Segoe UI", 11),
            text_color=AppColors.TEXT_SECONDARY
        ).pack(side="left", padx=(15, 5))
        
        self.preview_track_selector_var = ctk.StringVar(value="Track 1")
        self.preview_track_selector = ctk.CTkOptionMenu(
            btn_frame, 
            variable=self.preview_track_selector_var,
            values=["Track 1"], 
            width=110, 
            height=38,
            state="disabled",
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=8,
            font=("Segoe UI", 11)
        )
        self.preview_track_selector.pack(side="left", padx=5)
        
        detect_btn = ctk.CTkButton(
            btn_frame, 
            text="🔍 Detect Silence", 
            command=self.preview_detect_silence,
            height=38, 
            width=150, 
            font=("Segoe UI", 13, "bold"),
            fg_color=AppColors.INFO,
            hover_color=AppColors.PRIMARY_DARK,
            corner_radius=8
        )
        detect_btn.pack(side="left", padx=5)
        
        # Export button - process video with current silence selections
        self.export_btn = ctk.CTkButton(
            btn_frame, 
            text="💾 Export Video", 
            command=self.preview_export_video,
            height=38, 
            width=150, 
            font=("Segoe UI", 13, "bold"),
            fg_color=AppColors.SUCCESS,
            hover_color=AppColors.SUCCESS_HOVER,
            corner_radius=8,
            state="disabled"  # Disabled until silence is detected
        )
        self.export_btn.pack(side="left", padx=5)
        
        # Processing options frame (encoder, format, trim) - below header
        self.options_frame = ctk.CTkFrame(
            self.parent,
            fg_color=AppColors.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=AppColors.BORDER
        )
        self.options_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        self.options_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Encoder selection
        encoder_frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        encoder_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=10)
        ctk.CTkLabel(
            encoder_frame,
            text="🎮 Video Encoder:",
            font=("Segoe UI", 11, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).pack(pady=(0, 5))
        self.encoder_var = ctk.StringVar(value="Detecting...")
        self.option_encoder = ctk.CTkOptionMenu(
            encoder_frame,
            values=["Detecting..."],
            variable=self.encoder_var,
            state="disabled",
            height=32,
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=6,
            font=("Segoe UI", 10)
        )
        self.option_encoder.pack(fill="x", padx=5)
        
        # Output format selection
        format_frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        format_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=10)
        ctk.CTkLabel(
            format_frame,
            text="📺 Output Format:",
            font=("Segoe UI", 11, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).pack(pady=(0, 5))
        self.format_var = ctk.StringVar(value="MP4")
        self.option_format = ctk.CTkOptionMenu(
            format_frame,
            values=["MP4", "MKV", "AVI", "MOV"],
            variable=self.format_var,
            height=32,
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=6,
            font=("Segoe UI", 10)
        )
        self.option_format.pack(fill="x", padx=5)
        
        # Save destination
        save_frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        save_frame.grid(row=0, column=2, sticky="ew", padx=5, pady=10)
        ctk.CTkLabel(
            save_frame,
            text="💾 Save Location:",
            font=("Segoe UI", 11, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).pack(pady=(0, 5))
        self.save_path_var = ctk.StringVar(value="Not selected")
        self.save_path_label = ctk.CTkLabel(
            save_frame,
            textvariable=self.save_path_var,
            font=("Segoe UI", 9),
            text_color=AppColors.TEXT_MUTED,
            anchor="w",
            wraplength=200
        )
        self.save_path_label.pack(fill="x", padx=5, pady=(0, 5))
        self.button_save = ctk.CTkButton(
            save_frame,
            text="📁 Select Folder",
            command=self.select_save_destination,
            height=32,
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=6,
            font=("Segoe UI", 10)
        )
        self.button_save.pack(fill="x", padx=5)
        
        # Trim settings
        trim_frame = ctk.CTkFrame(self.options_frame, fg_color="transparent")
        trim_frame.grid(row=0, column=3, sticky="ew", padx=5, pady=10)
        ctk.CTkLabel(
            trim_frame,
            text="✂️ Trim Settings:",
            font=("Segoe UI", 11, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).pack(pady=(0, 5))
        trim_inner = ctk.CTkFrame(trim_frame, fg_color="transparent")
        trim_inner.pack(fill="x", padx=5)
        ctk.CTkLabel(trim_inner, text="Start (s):", font=("", 9)).pack(side="left", padx=2)
        self.trim_start_entry = ctk.CTkEntry(trim_inner, placeholder_text="0", width=80, height=28)
        self.trim_start_entry.pack(side="left", padx=2)
        ctk.CTkLabel(trim_inner, text="End (s):", font=("", 9)).pack(side="left", padx=2)
        self.trim_end_entry = ctk.CTkEntry(trim_inner, placeholder_text="Full", width=80, height=28)
        self.trim_end_entry.pack(side="left", padx=2)
        
        # Audio track analysis section (placed in a separate row after options)
        audio_analysis_frame = ctk.CTkFrame(
            self.parent,
            fg_color=AppColors.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=AppColors.BORDER
        )
        audio_analysis_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        audio_analysis_frame.grid_columnconfigure(0, weight=1)
        
        audio_header = ctk.CTkFrame(audio_analysis_frame, fg_color="transparent")
        audio_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        audio_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            audio_header,
            text="🎵 Audio Track Details",
            font=("Segoe UI", 13, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w")
        
        self.button_analyze_tracks = ctk.CTkButton(
            audio_header,
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
        self.button_analyze_tracks.grid(row=0, column=1, sticky="e")
        
        self.audio_info_textbox = ctk.CTkTextbox(
            audio_analysis_frame,
            height=100,
            font=("Consolas", 10),
            fg_color=AppColors.BG_DARK,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=6,
            state="disabled"
        )
        self.audio_info_textbox.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        
        # Update grid row configuration to accommodate options frame
        self.parent.grid_rowconfigure(1, weight=0)  # Options + audio analysis frames (fixed height)
        self.parent.grid_rowconfigure(2, weight=1)  # Main content (timeline + preview)
        self.parent.grid_rowconfigure(3, weight=0)  # Console section (fixed height)
        
        # Status label with improved styling (exactly as original)
        self.preview_status = ctk.CTkLabel(
            header_frame, 
            text="📂 Load a video to begin analysis...",
            font=("Segoe UI", 11),
            anchor="w", 
            text_color=AppColors.TEXT_MUTED
        )
        self.preview_status.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 12), sticky="ew")
        
        # Interactive Timeline (left side) - Enhanced styling (exactly as original)
        self.preview_timeline = InteractiveTimeline(
            self.parent, 
            fg_color=AppColors.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=AppColors.BORDER,
            on_time_click=self.on_preview_timeline_click
        )
        self.preview_timeline.grid(row=2, column=0, sticky="nsew", padx=(12, 6), pady=(0, 12))
        
        # Frame Preview (right side) - Enhanced styling (exactly as original)
        self.preview_frame = FramePreview(
            self.parent,
            fg_color=AppColors.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=AppColors.BORDER
        )
        self.preview_frame.grid(row=2, column=1, sticky="nsew", padx=(6, 12), pady=(0, 12))
        
        # Console/Status textbox section (matching main tab)
        console_frame = ctk.CTkFrame(
            self.parent,
            fg_color=AppColors.BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color=AppColors.BORDER,
            height=150
        )
        console_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        console_frame.grid_propagate(False)
        console_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            console_frame,
            text="📋 Console Output",
            font=("Segoe UI", 13, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=0, column=0, padx=12, pady=(12, 8), sticky="w")
        
        self.status_textbox = ctk.CTkTextbox(
            console_frame,
            state="disabled",
            fg_color=AppColors.BG_DARK,
            font=("Consolas", 10),
            corner_radius=6,
            border_width=1,
            border_color=AppColors.BORDER,
            height=100
        )
        self.status_textbox.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
    
    def preview_load_video(self):
        """
        Load a video file for preview and analysis.
        """
        # Open file dialog
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        # Load video into frame preview
        success = self.preview_frame.load_video(file_path, self.ffprobe_path)
        
        if not success:
            self.preview_status.configure(text="❌ Failed to load video file")
            return
        
        # Store video path
        self.video_path = file_path
        
        # Get video duration
        self.duration = get_video_duration(Path(file_path), self.ffprobe_path, self.update_status)
        
        # Detect audio tracks
        self.audio_tracks = get_audio_tracks(Path(file_path), self.ffprobe_path, self.update_status)
        
        # Store available tracks for analysis
        self.available_tracks = self.audio_tracks.copy() if self.audio_tracks else []
        
        # Update track selector
        if self.audio_tracks:
            # Use the actual track names from FFmpeg (which include stream index)
            track_names = [track["name"] for track in self.audio_tracks]
            self.preview_track_selector.configure(values=track_names, state="normal")
            self.preview_track_selector_var.set(track_names[0])
            # Enable analyze button
            if hasattr(self, 'button_analyze_tracks'):
                self.button_analyze_tracks.configure(state="normal")
        else:
            self.preview_track_selector.configure(values=["No audio tracks"], state="disabled")
            if hasattr(self, 'button_analyze_tracks'):
                self.button_analyze_tracks.configure(state="disabled")
        
        # Detect available encoders
        self.available_encoders = get_available_encoders(self.ffmpeg_path, self.update_status)
        if self.available_encoders:
            self.option_encoder.configure(values=self.available_encoders, state="normal")
            self.encoder_var.set(self.available_encoders[0])
        
        # Update timeline with video info
        self.preview_timeline.update_timeline([], self.duration)
        
        # Update status
        self.preview_status.configure(text=f"✅ Loaded: {Path(file_path).name} ({format_time(self.duration)})")
        
        # Notify main tab about video loaded
        if self.on_video_loaded:
            self.on_video_loaded(self.video_path, self.duration, self.audio_tracks)
    
    def preview_detect_silence(self):
        """
        Detect silence in the selected audio track.
        """
        if not self.video_path or not self.audio_tracks:
            return
        
        # Get selected track index
        selected_track_name = self.preview_track_selector_var.get()
        
        # Find the track that matches the selected name
        track_index = None
        for track in self.audio_tracks:
            if track["name"] == selected_track_name:
                track_index = track["index"]  # Use the actual FFmpeg stream index
                break
        
        if track_index is None:
            self.preview_status.configure(text="❌ Error: Could not find selected track")
            return
        
        # Get settings
        settings_dict = {
            "silence_db": self.settings.get("silence_db", -40),
            "silence_duration": self.settings.get("silence_duration", 0.7),
            "pad_before": self.settings.get("pad_before", 0.1),
            "pad_after": self.settings.get("pad_after", 0.0),
            "filter_length_threshold": self.settings.get("filter_length_threshold", 4096)
        }
        
        # Detect silence
        self.preview_status.configure(text="🔍 Detecting silence...")
        ffmpeg_log = detect_silence(
            Path(self.video_path), 
            track_index, 
            self.ffmpeg_path, 
            settings_dict, 
            self.update_status
        )
        
        # Parse segments
        self.detected_segments = parse_segments(
            ffmpeg_log, 
            self.duration, 
            settings_dict, 
            self.update_status
        )
        
        # Extract waveforms for ALL audio tracks (exactly as original)
        self.preview_status.configure(text="📊 Extracting waveforms...")
        
        # Convert audio_tracks format for WaveformGenerator
        # WaveformGenerator expects "audio_index" and "stream_index" fields
        waveform_tracks = []
        for i, track in enumerate(self.audio_tracks):
            waveform_tracks.append({
                "audio_index": i,  # 0-based index for WaveformGenerator
                "stream_index": track["index"],  # FFmpeg stream index
                "name": track["name"],
                "codec": track["codec"],
                "language": track["language"]
            })
        
        waveforms = WaveformGenerator.extract_audio_waveforms_all_tracks(
            self.video_path, 
            self.ffmpeg_path, 
            waveform_tracks, 
            self.update_status
        )
        
        # Update timeline with segments AND waveforms
        self.preview_timeline.update_timeline(self.detected_segments, self.duration, waveforms)
        
        # Update status
        segment_count = len(self.detected_segments)
        track_count = len(waveforms)
        self.preview_status.configure(text=f"✅ Detected {segment_count} segments | {track_count} waveforms | Click timeline to preview")
        
        # Enable export button now that we have segments
        self.export_btn.configure(state="normal")
        
        # Notify main tab about silence detection completed
        if self.on_silence_detected:
            self.on_silence_detected(self.detected_segments, track_index)
    
    def select_save_destination(self):
        """Select save destination for exported video."""
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if output_dir:
            self.save_path = output_dir
            # Show shortened path if too long
            display_path = output_dir if len(output_dir) <= 40 else "..." + output_dir[-37:]
            self.save_path_var.set(display_path)
            self.preview_status.configure(text=f"✅ Save location: {Path(output_dir).name}")
    
    def preview_export_video(self):
        """
        Export video with current silence segment selections.
        
        This processes the video with all segments marked as keep=True:
        - Green segments (audible) - always kept
        - Gray segments (good silence) - kept if keep=True
        - Red segments (bad silence) - removed if keep=False
        
        The export respects your timeline selections!
        """
        if not self.video_path or not self.detected_segments:
            messagebox.showwarning("No Video", "Please load a video and detect silence first.")
            return
        
        # Check if save path is selected
        if not self.save_path:
            messagebox.showwarning("No Save Location", "Please select a save destination first.")
            return
        
        # Get selected encoder
        selected_encoder = self.encoder_var.get()
        if not selected_encoder or selected_encoder == "Detecting...":
            messagebox.showwarning("No Encoder", "Please wait for encoder detection or select one manually.")
            return
        
        # Get encoder parameters
        if selected_encoder == "Automatic (Best GPU)":
            # Use the first hardware encoder available
            for enc_name, (enc_id, params) in ENCODER_OPTIONS.items():
                if enc_name in self.available_encoders and enc_name != "CPU (x264)":
                    video_params = params
                    break
            else:
                video_params = ENCODER_OPTIONS["CPU (x264)"][1]
        else:
            video_params = ENCODER_OPTIONS.get(selected_encoder, ("", ""))[1]
            if not video_params:
                messagebox.showerror("Invalid Encoder", f"Encoder '{selected_encoder}' not found.")
                return
        
        # Get output format
        output_format = self.format_var.get().lower()
        
        # Get settings
        settings_dict = {
            "silence_db": self.settings.get("silence_db", -40),
            "silence_duration": self.settings.get("silence_duration", 0.7),
            "pad_before": self.settings.get("pad_before", 0.1),
            "pad_after": self.settings.get("pad_after", 0.0),
            "filter_length_threshold": self.settings.get("filter_length_threshold", 4096)
        }
        
        # Count segments to keep for user feedback
        segments_to_keep = [seg for seg in self.detected_segments if seg.get('keep', True)]
        audible_count = sum(1 for seg in segments_to_keep if seg.get('type') == 'audible')
        silence_count = sum(1 for seg in segments_to_keep if seg.get('type') == 'silent')
        
        # Confirm export
        confirm_msg = (
            f"Export video with current selections?\n\n"
            f"Will keep:\n"
            f"  • {audible_count} audible segments (green)\n"
            f"  • {silence_count} silence segments (gray - good silence)\n\n"
            f"Will remove:\n"
            f"  • Red silence segments (bad silence)\n\n"
            f"Encoder: {selected_encoder}\n"
            f"Format: {output_format.upper()}\n"
            f"Save to: {Path(self.save_path).name}"
        )
        
        if not messagebox.askyesno("Confirm Export", confirm_msg):
            return
        
        # Disable export button during processing
        self.export_btn.configure(state="disabled", text="⏳ Processing...")
        
        # Create progress callback
        def progress_callback(percentage, eta, speed):
            self.preview_status.configure(
                text=f"⏳ Processing: {percentage:.1f}% | ETA: {eta} | Speed: {speed:.1f}x"
            )
        
        # Start processing in background thread
        def process_thread():
            try:
                process_video_logic(
                    video_path=self.video_path,
                    output_dir=self.save_path,
                    output_format=output_format,
                    video_params=video_params,
                    all_audio_tracks=self.audio_tracks,
                    silence_track_index=self.audio_tracks[0]["index"] if self.audio_tracks else 0,
                    ffmpeg_path=self.ffmpeg_path,
                    ffprobe_path=self.ffprobe_path,
                    settings=settings_dict,
                    status_callback=self.update_status,
                    progress_callback=progress_callback,
                    segments=self.detected_segments  # Use current segments with user modifications
                )
                
                # Success
                self.preview_status.configure(text="✅ Export complete! Check output directory.")
                messagebox.showinfo("Export Complete", 
                    f"Video exported successfully!\n\n"
                    f"Saved to: {self.save_path}\n"
                    f"File: {Path(self.video_path).stem}_final.{output_format}")
                
            except Exception as e:
                self.preview_status.configure(text=f"❌ Export failed: {str(e)}")
                messagebox.showerror("Export Failed", f"Error during export:\n{str(e)}")
            
            finally:
                # Re-enable export button
                self.export_btn.configure(state="normal", text="💾 Export Video")
        
        # Start processing thread
        thread = threading.Thread(target=process_thread, daemon=True)
        thread.start()
    
    def on_preview_timeline_click(self, time_seconds: float):
        """
        Handle timeline click events.
        
        Args:
            time_seconds: Time in seconds where the user clicked
        """
        if self.preview_frame:
            self.preview_frame.show_frame_at_time(time_seconds)
    
    def update_status(self, message: str):
        """
        Update the status label and console textbox with a message.
        
        Args:
            message: Status message to display
        """
        # Update status label
        if self.preview_status:
            self.preview_status.configure(text=message)
        
        # Update console textbox
        if self.status_textbox:
            self.status_textbox.configure(state="normal")
            self.status_textbox.insert("end", message + "\n")
            self.status_textbox.see("end")
            self.status_textbox.configure(state="disabled")