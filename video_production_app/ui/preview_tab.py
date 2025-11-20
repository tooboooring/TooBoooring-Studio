"""
Preview and Analysis tab for Video Production App.

This module contains the preview tab functionality with professional panel-based layout.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable, List
import threading

from ..core.ffmpeg_wrapper import get_audio_tracks, get_video_duration, analyze_audio_track_content
from ..core.silence_detector import detect_silence, parse_segments
from ..core.video_processor import process_video_logic
from ..core.settings_manager import SettingsManager
from .widgets.vlc_player import VLCPlayer
from .widgets.timeline import InteractiveTimeline
from .widgets.waveform import WaveformGenerator
from ..utils.colors import AppColors
from ..utils.helpers import format_time, load_icon, add_tooltip
from ..config import ENCODER_OPTIONS, AI_MODELS
from ..ai_analysis.orchestrator import apply_decisions_to_segments
from datetime import datetime


class PreviewTab:
    """
    Preview and Analysis tab for the Video Production App.
    
    Professional panel-based layout similar to DaVinci Resolve/Premiere Pro.
    """
    
    def __init__(self, parent, settings: SettingsManager, 
                 ffmpeg_path: str = "", ffprobe_path: str = "", ffplay_path: str = "",
                 available_encoders: Optional[List[str]] = None,
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
            available_encoders: List of available encoder names (detected at app startup)
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
        
        # State variables
        self.video_path = ""
        self.audio_tracks = []
        self.available_tracks = []
        self.detected_segments = []
        self.duration = 0
        self.save_path = ""
        self.available_encoders = available_encoders if available_encoders else ["CPU (x264)"]
        
        # Analysis history for toggling between different AI runs
        self.analysis_history = []  # List of dicts: {label, result, model_name, timestamp}
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """
        Set up the preview tab with professional panel-based layout.
        
        Layout:
        - Top: Toolbar with icon buttons
        - Main: 2-column layout (Left: VLC Player, Right: Audio Details + Trim)
        - Bottom: Interactive Timeline
        """
        # Configure grid
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(1, weight=2)  # Main area (player + right panel) - takes 2x space
        self.parent.grid_rowconfigure(2, weight=1)  # Timeline (vertically scalable) - takes 1x space
        
        # === TOP TOOLBAR ===
        toolbar = ctk.CTkFrame(
            self.parent,
            fg_color=AppColors.BG_MEDIUM,
            border_width=0,
            border_color=AppColors.BORDER,
            height=40
        )
        toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        toolbar.grid_propagate(False)
        toolbar.grid_columnconfigure(1, weight=1)
        
        # Left: Buttons with text labels (matching web UI style)
        btn_container = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_container.grid(row=0, column=0, sticky="w", padx=10, pady=0)
        
        # Load Video button
        load_btn = ctk.CTkButton(
            btn_container,
            text="Load Video",
            width=100,
            height=28,
            command=self.preview_load_video,
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=4,
            font=("Segoe UI", 11, "bold")
        )
        load_btn.grid(row=0, column=0, padx=3)
        add_tooltip(load_btn, "Load Video File")
        
        # Detect Silence button
        detect_btn = ctk.CTkButton(
            btn_container,
            text="Detect Silence",
            width=120,
            height=28,
            command=self.preview_detect_silence,
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=4,
            font=("Segoe UI", 11, "bold")
        )
        detect_btn.grid(row=0, column=1, padx=3)
        add_tooltip(detect_btn, "Detect Silence")
        
        # Export button (matching web UI style)
        self.export_btn = ctk.CTkButton(
            btn_container,
            text="Export Video",
            width=120,
            height=28,
            command=self.preview_export_video,
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=4,
            font=("Segoe UI", 11, "bold"),
            state="disabled"
        )
        self.export_btn.grid(row=0, column=2, padx=3)
        add_tooltip(self.export_btn, "Export Video")
        
        # Center: Track selector
        track_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        track_frame.grid(row=0, column=1, sticky="", padx=10)
        
        ctk.CTkLabel(
            track_frame,
            text="Track:",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_SECONDARY
        ).grid(row=0, column=0, padx=5)
        
        self.preview_track_selector_var = ctk.StringVar(value="Track 1")
        self.preview_track_selector = ctk.CTkOptionMenu(
            track_frame,
            variable=self.preview_track_selector_var,
            values=["Track 1"],
            width=150,
            height=28,
            state="disabled",
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=4,
            font=("Segoe UI", 12)
        )
        self.preview_track_selector.grid(row=0, column=1, padx=5)
        
        # Right: Status label
        self.preview_status = ctk.CTkLabel(
            toolbar,
            text="Load a video to begin",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_SECONDARY
        )
        self.preview_status.grid(row=0, column=2, sticky="e", padx=10, pady=5)
        
        # === MAIN AREA (Fully Resizable Panels using PanedWindow) ===
        import tkinter as tk
        
        # Main horizontal PanedWindow: Left (Player) | Right (Audio/Console/Trim)
        main_paned = tk.PanedWindow(
            self.parent,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            sashrelief=tk.FLAT,
            bg=AppColors.BG_DARK,
            bd=0,
            sashpad=1
        )
        main_paned.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        
        # === LEFT: VLC Player Panel ===
        player_panel = ctk.CTkFrame(
            main_paned,
            fg_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=4
        )
        main_paned.add(player_panel, minsize=300, width=600)
        player_panel.grid_rowconfigure(0, weight=1)
        player_panel.grid_columnconfigure(0, weight=1)
        
        # Panel header
        player_header = ctk.CTkFrame(
            player_panel,
            fg_color=AppColors.BG_LIGHT,
            border_width=0,
            height=30
        )
        player_header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        player_header.grid_propagate(False)
        player_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            player_header,
            text="Preview",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=12, pady=6)
        
        self.vlc_player = VLCPlayer(
            player_panel,
            fg_color="transparent",
            corner_radius=0,
            border_width=0
        )
        self.vlc_player.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        player_panel.grid_rowconfigure(1, weight=1)
        
        # Store references for toggling
        self.main_paned = main_paned
        self.player_panel = player_panel
        
        # === RIGHT: Vertical PanedWindow (Audio | Console | Trim) ===
        # Create a container frame for the right panel with toggle button
        self.right_container = ctk.CTkFrame(
            main_paned,
            fg_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=4
        )
        main_paned.add(self.right_container, minsize=300, width=400)
        self.right_container.grid_columnconfigure(0, weight=1)
        self.right_container.grid_rowconfigure(1, weight=1)
        
        # Panel header with toggle button
        right_header = ctk.CTkFrame(
            self.right_container,
            fg_color=AppColors.BG_LIGHT,
            border_width=0,
            height=30
        )
        right_header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        right_header.grid_propagate(False)
        right_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            right_header,
            text="Controls",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=12, pady=6)
        
        # Toggle button for collapsing right panel (in header)
        self.right_panel_toggle_btn = ctk.CTkButton(
            right_header,
            text="◀",
            width=24,
            height=24,
            command=self.toggle_right_panel,
            fg_color="transparent",
            hover_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=3,
            font=("Segoe UI", 10)
        )
        self.right_panel_toggle_btn.grid(row=0, column=1, sticky="e", padx=8, pady=3)
        add_tooltip(self.right_panel_toggle_btn, "Collapse/Expand Right Panel")
        
        # Store reference to right panel and its visibility state
        self.right_panel_visible = True
        
        right_paned = tk.PanedWindow(
            self.right_container,
            orient=tk.VERTICAL,
            sashwidth=4,
            sashrelief=tk.FLAT,
            bg=AppColors.BG_MEDIUM,
            bd=0,
            sashpad=1
        )
        right_paned.grid(row=1, column=0, sticky="nsew")
        self.right_panel = right_paned  # Store reference for toggling
        
        # === Export & Trim Settings Row (Top - side by side, equal size) ===
        export_trim_row = tk.PanedWindow(
            right_paned,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            sashrelief=tk.FLAT,
            bg=AppColors.BG_MEDIUM,
            bd=0,
            sashpad=1
        )
        right_paned.add(export_trim_row, minsize=140, height=140)
        
        # Export Settings Panel (Left, 50% width)
        export_panel = ctk.CTkFrame(
            export_trim_row,
            fg_color=AppColors.BG_MEDIUM,
            border_width=0,
            border_color=AppColors.BORDER
        )
        export_trim_row.add(export_panel, minsize=200)
        
        export_section = ctk.CTkFrame(
            export_panel,
            fg_color="transparent"
        )
        export_section.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            export_section,
            text="Export Settings",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 10))
        
        # Encoder selection
        encoder_inner = ctk.CTkFrame(export_section, fg_color="transparent")
        encoder_inner.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(encoder_inner, text="Encoder:", font=("Segoe UI", 11), width=70).pack(side="left", padx=5)
        # Use available encoders from app startup, or default to CPU encoder
        encoder_values = self.available_encoders if self.available_encoders else ["CPU (x264)"]
        self.encoder_var = ctk.StringVar(value=encoder_values[0] if encoder_values else "CPU (x264)")
        self.option_encoder = ctk.CTkOptionMenu(
            encoder_inner,
            values=encoder_values,
            variable=self.encoder_var,
            state="normal",
            width=180,
            height=28,
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=4,
            font=("Segoe UI", 11)
        )
        self.option_encoder.pack(side="left", padx=5, fill="x", expand=True)
        
        # Format selection
        format_inner = ctk.CTkFrame(export_section, fg_color="transparent")
        format_inner.pack(fill="x")
        
        ctk.CTkLabel(format_inner, text="Format:", font=("Segoe UI", 11), width=70).pack(side="left", padx=5)
        self.format_var = ctk.StringVar(value="MP4")
        self.option_format = ctk.CTkOptionMenu(
            format_inner,
            values=["MP4", "MKV"],
            variable=self.format_var,
            width=180,
            height=28,
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=4,
            font=("Segoe UI", 11)
        )
        self.option_format.pack(side="left", padx=5, fill="x", expand=True)
        
        # Save Destination selection
        save_dest_inner = ctk.CTkFrame(export_section, fg_color="transparent")
        save_dest_inner.pack(fill="x", pady=(5, 0))
        
        ctk.CTkLabel(save_dest_inner, text="Save:", font=("Segoe UI", 11), width=70).pack(side="left", padx=5)
        self.save_dest_btn = ctk.CTkButton(
            save_dest_inner,
            text="Select Folder",
            width=120,
            height=28,
            command=self.select_save_destination,
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=4,
            font=("Segoe UI", 11, "bold")
        )
        self.save_dest_btn.pack(side="left", padx=5)
        
        self.save_dest_label = ctk.CTkLabel(
            save_dest_inner,
            text="Not selected",
            font=("Segoe UI", 10),
            text_color=AppColors.TEXT_SECONDARY,
            anchor="w"
        )
        self.save_dest_label.pack(side="left", padx=5, fill="x", expand=True)
        
        # AI Model Selection
        ai_model_inner = ctk.CTkFrame(export_section, fg_color="transparent")
        ai_model_inner.pack(fill="x", pady=(5, 0))
        
        ctk.CTkLabel(ai_model_inner, text="AI Model:", font=("Segoe UI", 11), width=70).pack(side="left", padx=5)
        model_names = list(AI_MODELS.keys())
        self.ai_model_var = ctk.StringVar(value=model_names[1] if len(model_names) > 1 else model_names[0])  # Default to 70B
        self.ai_model_selector = ctk.CTkOptionMenu(
            ai_model_inner,
            values=model_names,
            variable=self.ai_model_var,
            command=self.update_cost_estimate,
            width=180,
            height=28,
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=4,
            font=("Segoe UI", 10)
        )
        self.ai_model_selector.pack(side="left", padx=5, fill="x", expand=True)
        
        # Cost Estimate Label
        self.cost_label = ctk.CTkLabel(
            export_section,
            text="Est. Cost: $0.0000",
            font=("Segoe UI", 9),
            text_color=AppColors.TEXT_SECONDARY,
            anchor="w"
        )
        self.cost_label.pack(anchor="w", pady=(3, 0), padx=10)
        
        # Analysis History Selector
        history_inner = ctk.CTkFrame(export_section, fg_color="transparent")
        history_inner.pack(fill="x", pady=(5, 0))
        
        ctk.CTkLabel(history_inner, text="History:", font=("Segoe UI", 11), width=70).pack(side="left", padx=5)
        self.history_var = ctk.StringVar(value="No runs yet")
        self.history_selector = ctk.CTkOptionMenu(
            history_inner,
            values=["No runs yet"],
            variable=self.history_var,
            command=self.load_history_item,
            width=180,
            height=28,
            state="disabled",
            fg_color=AppColors.BG_LIGHT,
            button_color=AppColors.PRIMARY,
            button_hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=4,
            font=("Segoe UI", 10)
        )
        self.history_selector.pack(side="left", padx=5, fill="x", expand=True)
        
        # Trim Settings Panel (Right, in same row as Export, 50% width)
        trim_panel = ctk.CTkFrame(
            export_trim_row,
            fg_color=AppColors.BG_MEDIUM,
            border_width=0,
            border_color=AppColors.BORDER
        )
        export_trim_row.add(trim_panel, minsize=150)
        
        trim_section = ctk.CTkFrame(
            trim_panel,
            fg_color="transparent"
        )
        trim_section.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            trim_section,
            text="Trim Settings",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 10))
        
        trim_inner = ctk.CTkFrame(trim_section, fg_color="transparent")
        trim_inner.pack(fill="x")
        
        ctk.CTkLabel(trim_inner, text="Start (s):", font=("Segoe UI", 11), width=70).pack(side="left", padx=5)
        self.trim_start_entry = ctk.CTkEntry(
            trim_inner, 
            placeholder_text="0", 
            width=100, 
            height=28,
            fg_color=AppColors.BG_LIGHT,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=3,
            font=("Segoe UI", 11),
            text_color=AppColors.TEXT_PRIMARY
        )
        self.trim_start_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        trim_inner2 = ctk.CTkFrame(trim_section, fg_color="transparent")
        trim_inner2.pack(fill="x", pady=(5, 0))
        
        ctk.CTkLabel(trim_inner2, text="End (s):", font=("Segoe UI", 11), width=70).pack(side="left", padx=5)
        self.trim_end_entry = ctk.CTkEntry(
            trim_inner2, 
            placeholder_text="Full", 
            width=100, 
            height=28,
            fg_color=AppColors.BG_LIGHT,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=3,
            font=("Segoe UI", 11),
            text_color=AppColors.TEXT_PRIMARY
        )
        self.trim_end_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # === Audio Track & Console Row (side by side, equal size) ===
        audio_console_row = tk.PanedWindow(
            right_paned,
            orient=tk.HORIZONTAL,
            sashwidth=4,
            sashrelief=tk.FLAT,
            bg=AppColors.BG_MEDIUM,
            bd=0,
            sashpad=1
        )
        right_paned.add(audio_console_row, minsize=200, height=200)
        
        # Audio Track Details Panel (Left, 50% width)
        audio_panel = ctk.CTkFrame(
            audio_console_row,
            fg_color=AppColors.BG_MEDIUM,
            border_width=0,
            border_color=AppColors.BORDER
        )
        audio_console_row.add(audio_panel, minsize=200)
        audio_panel.grid_columnconfigure(0, weight=1)
        audio_panel.grid_rowconfigure(1, weight=1)
        
        # Audio Track Details header
        audio_header = ctk.CTkFrame(audio_panel, fg_color="transparent")
        audio_header.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        audio_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            audio_header,
            text="Audio Track Details",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w")
        
        self.button_analyze_tracks = ctk.CTkButton(
            audio_header,
            text="Analyze All Tracks",
            width=140,
            height=28,
            command=self.analyze_all_tracks,
            fg_color=AppColors.PRIMARY,
            hover_color=AppColors.PRIMARY_HOVER,
            corner_radius=4,
            font=("Segoe UI", 11, "bold"),
            state="disabled"
        )
        self.button_analyze_tracks.grid(row=0, column=1, sticky="e", padx=5)
        add_tooltip(self.button_analyze_tracks, "Analyze All Audio Tracks")
        
        self.audio_info_textbox = ctk.CTkTextbox(
            audio_panel,
            font=("Consolas", 10),
            fg_color=AppColors.BG_DARK,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=4,
            state="disabled"
        )
        self.audio_info_textbox.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        
        # Console Output Panel (Right, in same row as Audio, 50% width)
        console_panel = ctk.CTkFrame(
            audio_console_row,
            fg_color=AppColors.BG_MEDIUM,
            border_width=0,
            border_color=AppColors.BORDER
        )
        audio_console_row.add(console_panel, minsize=200)
        console_panel.grid_columnconfigure(0, weight=1)
        console_panel.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            console_panel,
            text="Console Output",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=0, column=0, padx=10, pady=(10, 8), sticky="w")
        
        self.status_textbox = ctk.CTkTextbox(
            console_panel,
            state="disabled",
            fg_color=AppColors.BG_DARK,
            font=("Consolas", 10),
            corner_radius=4,
            border_width=1,
            border_color=AppColors.BORDER
        )
        self.status_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        # === Progress Panel (Below Audio/Console row) ===
        progress_panel = ctk.CTkFrame(
            right_paned,
            fg_color=AppColors.BG_MEDIUM,
            border_width=0,
            border_color=AppColors.BORDER
        )
        right_paned.add(progress_panel, minsize=80, height=100)
        progress_panel.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            progress_panel,
            text="Progress",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=0, column=0, padx=10, pady=(10, 8), sticky="w")
        
        # Progress percentage
        self.progress_percentage = ctk.CTkLabel(
            progress_panel,
            text="0%",
            font=("Segoe UI", 24, "bold"),
            text_color=AppColors.PRIMARY
        )
        self.progress_percentage.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        # Progress bar (matching web UI style)
        self.progress_bar = ctk.CTkProgressBar(
            progress_panel,
            height=20,
            corner_radius=3,
            border_width=1,
            border_color=AppColors.BORDER,
            progress_color=AppColors.PRIMARY,
            fg_color=AppColors.BG_DARK
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        # Progress details (ETA, speed)
        self.progress_details = ctk.CTkLabel(
            progress_panel,
            text="Ready",
            font=("Segoe UI", 10),
            text_color=AppColors.TEXT_SECONDARY
        )
        self.progress_details.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="w")
        
        # === BOTTOM: Timeline Panel (Vertically Scalable & Collapsible) ===
        # Create a container frame for the timeline with toggle button
        self.timeline_container = ctk.CTkFrame(
            self.parent,
            fg_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=4
        )
        self.timeline_container.grid(row=2, column=0, sticky="nsew", padx=2, pady=2)
        self.timeline_container.grid_columnconfigure(0, weight=1)
        self.timeline_container.grid_rowconfigure(1, weight=1)  # Timeline content row
        
        # Timeline header (matching web UI style)
        timeline_header = ctk.CTkFrame(
            self.timeline_container,
            fg_color=AppColors.BG_LIGHT,
            border_width=0,
            height=30
        )
        timeline_header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        timeline_header.grid_propagate(False)
        timeline_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            timeline_header,
            text="Interactive Timeline",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=12, pady=6)
        
        # Toggle button in header (matching web UI style)
        self.timeline_toggle_btn = ctk.CTkButton(
            timeline_header,
            text="▼",
            width=24,
            height=24,
            command=self.toggle_timeline,
            fg_color="transparent",
            hover_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=3,
            font=("Segoe UI", 10)
        )
        self.timeline_toggle_btn.grid(row=0, column=1, sticky="e", padx=8, pady=3)
        add_tooltip(self.timeline_toggle_btn, "Collapse/Expand Timeline")
        
        # Create a container for the timeline content below the header
        timeline_content = ctk.CTkFrame(
            self.timeline_container,
            fg_color=AppColors.BG_MEDIUM,
            border_width=0,
            border_color=AppColors.BORDER
        )
        timeline_content.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        timeline_content.grid_rowconfigure(0, weight=1)
        timeline_content.grid_columnconfigure(0, weight=1)
        
        # Update grid configuration
        self.timeline_container.grid_rowconfigure(1, weight=1)
        
        # Store reference to timeline panel and its visibility state
        self.timeline_visible = True
        self.timeline_panel = timeline_content  # Store reference for toggling
        
        self.preview_timeline = InteractiveTimeline(
            timeline_content,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
            on_time_click=self.on_preview_timeline_click
        )
        self.preview_timeline.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        
        # Set initial tooltip for AI model selector
        if hasattr(self, 'ai_model_selector') and hasattr(self, 'ai_model_var'):
            selected_model_name = self.ai_model_var.get()
            if selected_model_name and selected_model_name in AI_MODELS:
                model_info = AI_MODELS[selected_model_name]
                if "tooltip" in model_info:
                    add_tooltip(self.ai_model_selector, model_info["tooltip"])
    
    def preview_load_video(self):
        """Load a video file for preview and analysis."""
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        # Store video path
        self.video_path = file_path
        
        # Clear console
        if hasattr(self, 'status_textbox') and self.status_textbox:
            self.status_textbox.configure(state="normal")
            self.status_textbox.delete("1.0", "end")
            self.status_textbox.insert("end", f"📹 Loaded: {Path(file_path).name}\n")
            self.status_textbox.configure(state="disabled")
        
        # Get video duration
        self.duration = get_video_duration(Path(file_path), self.ffprobe_path, self.update_status)
        
        # Load video into VLC player
        if hasattr(self, 'vlc_player') and self.vlc_player:
            self.vlc_player.load_video(file_path, self.duration, [])
        
        # Detect audio tracks
        self.audio_tracks = get_audio_tracks(Path(file_path), self.ffprobe_path, self.update_status)
        
        # Store available tracks for analysis
        self.available_tracks = self.audio_tracks.copy() if self.audio_tracks else []
        
        # Update track selector
        if self.audio_tracks:
            track_names = [track["name"] for track in self.audio_tracks]
            self.preview_track_selector.configure(values=track_names, state="normal")
            self.preview_track_selector_var.set(track_names[0])
            if hasattr(self, 'button_analyze_tracks'):
                self.button_analyze_tracks.configure(state="normal")
        else:
            self.preview_track_selector.configure(values=["No audio tracks"], state="disabled")
            if hasattr(self, 'button_analyze_tracks'):
                self.button_analyze_tracks.configure(state="disabled")
        
        # Encoders are already detected at app startup, no need to detect again
        
        # Update timeline with video info
        self.preview_timeline.update_timeline([], self.duration)
        
        # Update status
        self.preview_status.configure(text=f"Loaded: {Path(file_path).name} ({format_time(self.duration)})")
        
        # Update cost estimate with new video duration
        self.update_cost_estimate()
        
        # Notify main tab about video loaded
        if self.on_video_loaded:
            self.on_video_loaded(self.video_path, self.duration, self.audio_tracks)
    
    def preview_detect_silence(self):
        """Detect silence in the selected audio track."""
        if not self.video_path or not self.audio_tracks:
            return
        
        # Get selected track index
        selected_track_name = self.preview_track_selector_var.get()
        track_index = None
        for track in self.audio_tracks:
            if track["name"] == selected_track_name:
                track_index = track["index"]
                break
        
        if track_index is None:
            self.preview_status.configure(text="Error: Could not find selected track")
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
        self.preview_status.configure(text="Detecting silence...")
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
        
        # Update VLC player with segments
        if hasattr(self, 'vlc_player') and self.vlc_player:
            self.vlc_player.segments = self.detected_segments
        
        # Extract waveforms
        self.preview_status.configure(text="Extracting waveforms...")
        waveform_tracks = []
        for i, track in enumerate(self.audio_tracks):
            waveform_tracks.append({
                "audio_index": i,
                "stream_index": track["index"],
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
        if self.detected_segments:
            self.preview_timeline.update_timeline(self.detected_segments, self.duration, waveforms)
            self.update_status(f"✅ Timeline updated with {len(self.detected_segments)} segments")
        else:
            self.update_status("⚠️ No segments detected")
        
        segment_count = len(self.detected_segments) if self.detected_segments else 0
        track_count = len(waveforms) if waveforms else 0
        self.preview_status.configure(text=f"Detected {segment_count} segments | {track_count} waveforms")
        
        # Enable export button
        self.export_btn.configure(state="normal")
        
        # Notify main tab
        if self.on_silence_detected:
            self.on_silence_detected(self.detected_segments, track_index)
    
    def analyze_all_tracks(self):
        """Analyze all audio tracks for content and display detailed information."""
        if not self.video_path or not self.available_tracks:
            messagebox.showwarning("Warning", "Please select a video file first")
            return
        
        # Ensure video is paused before analyzing (prevent auto-play)
        if hasattr(self, 'vlc_player') and self.vlc_player:
            if self.vlc_player.is_playing:
                self.vlc_player.media_player.pause()
                self.vlc_player.is_playing = False
                if self.vlc_player.play_icon:
                    self.vlc_player.play_pause_btn.configure(image=self.vlc_player.play_icon, text="")
                else:
                    self.vlc_player.play_pause_btn.configure(text="▶")
        
        # Disable button during analysis
        self.button_analyze_tracks.configure(state="disabled")
        
        # Clear previous analysis results
        self.audio_info_textbox.configure(state="normal")
        self.audio_info_textbox.delete("1.0", "end")
        
        # Show header
        header = ("Track    Codec      Channels    Status         Mean Volume   Max Volume\n"
                   "─────────────────────────────────────────────────────────────────────\n")
        self.audio_info_textbox.insert("end", header)
        self.audio_info_textbox.insert("end", "Analyzing tracks...\n\n")
        self.audio_info_textbox.configure(state="disabled")
        
        # Run analysis in background thread to keep UI responsive
        def analyze_thread():
            try:
                results = []
                for i, track in enumerate(self.available_tracks):
                    self.update_status(f"Analyzing Track {track['index']} ({i+1}/{len(self.available_tracks)})...")
                    
                    try:
                        analysis = analyze_audio_track_content(
                            Path(self.video_path), 
                            track['index'], 
                            self.ffmpeg_path
                        )
                        
                        track['analysis'] = analysis
                        
                        mean_str = f"{analysis['mean_volume']:.1f} dB" if analysis['mean_volume'] is not None else "N/A"
                        max_str = f"{analysis['max_volume']:.1f} dB" if analysis['max_volume'] is not None else "N/A"
                        
                        status_icon = ""
                        if analysis['is_silent']:
                            status_icon = "🔇 "
                        elif analysis['status'] == "Normal Audio":
                            status_icon = "🔊 "
                        elif analysis['status'] == "Quiet Audio":
                            status_icon = "🔉 "
                        elif analysis['status'] == "Loud Audio":
                            status_icon = "📢 "
                        
                        line = (f"{track['index']:<8} "
                               f"{track['codec']:<10} "
                               f"{track['channel_str']:<10} "
                               f"{status_icon}{analysis['status']:<13} "
                               f"{mean_str:<12} "
                               f"{max_str:<10}\n")
                        
                        results.append(line)
                        
                    except Exception as e:
                        error_line = f"{track['index']:<8} {track['codec']:<10} {track['channel_str']:<10} ❌ Error: {str(e)[:30]}...\n"
                        results.append(error_line)
                        self.update_status(f"Error analyzing Track {track['index']}: {e}")
                
                # Update UI in main thread
                self.parent.after(0, lambda: self._update_analysis_results(results))
                
            except Exception as e:
                self.parent.after(0, lambda: self.update_status(f"Analysis error: {e}"))
                self.parent.after(0, lambda: self.button_analyze_tracks.configure(state="normal"))
        
        thread = threading.Thread(target=analyze_thread, daemon=True)
        thread.start()
    
    def _update_analysis_results(self, results):
        """Update the audio info textbox with analysis results (called from main thread)."""
        self.audio_info_textbox.configure(state="normal")
        self.audio_info_textbox.delete("1.0", "end")
        
        # Show header
        header = ("Track    Codec      Channels    Status         Mean Volume   Max Volume\n"
                   "─────────────────────────────────────────────────────────────────────\n")
        self.audio_info_textbox.insert("end", header)
        
        # Insert all results
        for line in results:
            self.audio_info_textbox.insert("end", line)
        
        # Add completion message
        self.audio_info_textbox.insert("end", "\n✅ Analysis complete!\n")
        self.audio_info_textbox.insert("end", "🔇 = Silent/Empty track | 🔉 = Quiet | 🔊 = Normal | 📢 = Loud\n")
        self.audio_info_textbox.configure(state="disabled")
        
        self.update_status("Track analysis completed successfully")
        self.button_analyze_tracks.configure(state="normal")
    
    def select_save_destination(self):
        """Select save destination for exported video (matching web UI behavior)."""
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if output_dir:
            self.save_path = output_dir
            display_path = output_dir if len(output_dir) <= 50 else "..." + output_dir[-47:]
            self.preview_status.configure(text=f"Save location: {Path(output_dir).name}")
            # Update the label in export settings
            if hasattr(self, 'save_dest_label'):
                self.save_dest_label.configure(text=display_path, text_color=AppColors.SUCCESS)
    
    def preview_export_video(self):
        """Export video with current silence segment selections."""
        if not self.video_path or not self.detected_segments:
            messagebox.showwarning("No Video", "Please load a video and detect silence first.")
            return
        
        if not self.save_path:
            self.select_save_destination()
            if not self.save_path:
                return
        
        # Get selected encoder
        selected_encoder = self.encoder_var.get()
        if not selected_encoder or selected_encoder == "Detecting...":
            selected_encoder = self.available_encoders[0] if self.available_encoders else "CPU (x264)"
        
        # Get encoder parameters
        if selected_encoder == "Automatic (Best GPU)":
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
        
        # Confirm export
        if not messagebox.askyesno("Confirm Export", "Export video with current selections?"):
            return
        
        # Disable export button
        self.export_btn.configure(state="disabled")
        
        # Progress callback (must update UI on main thread)
        def progress_callback(percentage, eta, speed):
            # Schedule UI updates on main thread
            self.parent.after(0, lambda: self.progress_bar.set(percentage / 100.0))
            self.parent.after(0, lambda: self.progress_percentage.configure(text=f"{percentage:.1f}%"))
            self.parent.after(0, lambda: self.progress_details.configure(
                text=f"ETA: {eta} | Speed: {speed:.1f}x"
            ))
            self.parent.after(0, lambda: self.preview_status.configure(
                text=f"Processing: {percentage:.1f}% | ETA: {eta} | Speed: {speed:.1f}x"
            ))
        
        # Process in background thread
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
                    segments=self.detected_segments
                )
                
                # Reset progress
                self.progress_bar.set(100.0)
                self.progress_percentage.configure(text="100%")
                self.progress_details.configure(text="Complete!")
                self.preview_status.configure(text="Export complete! Check output directory.")
                messagebox.showinfo("Export Complete", 
                    f"Video exported successfully!\n\nSaved to: {self.save_path}")
                
            except Exception as e:
                # Reset progress on error
                self.progress_bar.set(0)
                self.progress_percentage.configure(text="0%")
                self.progress_details.configure(text="Failed")
                self.preview_status.configure(text=f"Export failed: {str(e)}")
                messagebox.showerror("Export Failed", f"Error during export:\n{str(e)}")
            
            finally:
                self.export_btn.configure(state="normal")
        
        thread = threading.Thread(target=process_thread, daemon=True)
        thread.start()
    
    def toggle_right_panel(self):
        """Toggle the visibility of the right panel (matching web UI behavior)."""
        if self.right_panel_visible:
            # Hide the right panel content (keep header visible)
            self.right_panel.grid_forget()
            self.right_panel_visible = False
            self.right_panel_toggle_btn.configure(text="▶")
            add_tooltip(self.right_panel_toggle_btn, "Expand Right Panel")
            
            # Minimize the right container in the PanedWindow
            try:
                self.main_paned.paneconfig(self.right_container, minsize=40, width=40)
            except:
                pass
            
            # Make VLC player expand to fill the space
            self.main_paned.update_idletasks()
        else:
            # Show the right panel
            self.right_panel.grid(row=1, column=0, sticky="nsew")
            self.right_panel_visible = True
            self.right_panel_toggle_btn.configure(text="◀")
            add_tooltip(self.right_panel_toggle_btn, "Collapse Right Panel")
            
            # Restore original size in PanedWindow
            try:
                self.main_paned.paneconfig(self.right_container, minsize=300, width=400)
            except:
                pass
            
            # Restore original layout
            self.main_paned.update_idletasks()
    
    def toggle_timeline(self):
        """Toggle the visibility of the timeline panel (matching web UI behavior)."""
        if self.timeline_visible:
            # Hide the timeline panel content (keep header visible)
            self.timeline_panel.grid_forget()
            self.timeline_visible = False
            self.timeline_toggle_btn.configure(text="▲")
            add_tooltip(self.timeline_toggle_btn, "Expand Timeline")
            
            # Adjust grid row weights to give more space to main area
            self.parent.grid_rowconfigure(1, weight=1)  # Main area takes all space
            self.parent.grid_rowconfigure(2, weight=0)  # Timeline takes no space
        else:
            # Show the timeline panel
            self.timeline_panel.grid(row=1, column=0, sticky="nsew")
            self.timeline_visible = True
            self.timeline_toggle_btn.configure(text="▼")
            add_tooltip(self.timeline_toggle_btn, "Collapse Timeline")
            
            # Restore original grid row weights
            self.parent.grid_rowconfigure(1, weight=2)  # Main area takes 2x space
            self.parent.grid_rowconfigure(2, weight=1)  # Timeline takes 1x space
    
    def on_preview_timeline_click(self, time_seconds: float):
        """Handle timeline click events."""
        if hasattr(self, 'vlc_player') and self.vlc_player:
            self.vlc_player.seek_to_time(time_seconds)
    
    def update_cost_estimate(self, *args):
        """
        Update the cost estimate display based on selected model and video duration.
        
        Formula:
        - estimated_words = duration_seconds * 2.5 (avg speaking rate)
        - estimated_tokens = estimated_words * 1.3 (tokens per word)
        - total_tokens = estimated_tokens * 2 (safety buffer for input + output)
        - cost = (total_tokens / 1_000_000) * price_per_million
        """
        if not hasattr(self, 'cost_label') or not hasattr(self, 'ai_model_var'):
            return
        
        # Get selected model
        selected_model_name = self.ai_model_var.get()
        if not selected_model_name or selected_model_name not in AI_MODELS:
            self.cost_label.configure(text="Est. Cost: $0.0000", text_color=AppColors.TEXT_SECONDARY)
            return
        
        # Get video duration
        if not self.duration or self.duration <= 0:
            self.cost_label.configure(
                text="Est. Cost: $0.0000 (Load video first)",
                text_color=AppColors.TEXT_SECONDARY
            )
            return
        
        # Calculate estimated cost
        model_info = AI_MODELS[selected_model_name]
        
        # Estimate tokens: 2.5 words/sec * 1.3 tokens/word = 3.25 tokens/sec
        # Add 2x safety buffer for input + output + context
        estimated_tokens = self.duration * 3.25 * 2
        
        # Calculate cost
        price_per_million = model_info["price"]
        cost = (estimated_tokens / 1_000_000) * price_per_million
        
        # Format tokens (e.g., 1500 -> 1.5k)
        if estimated_tokens >= 1000:
            tokens_str = f"{estimated_tokens/1000:.1f}k"
        else:
            tokens_str = f"{int(estimated_tokens)}"
        
        # Update tooltip dynamically with model details
        if "tooltip" in model_info and hasattr(self, 'ai_model_selector'):
            add_tooltip(self.ai_model_selector, model_info["tooltip"])
        
        # Update label with Cost, Tokens, and Description
        desc = model_info.get("desc", "")
        self.cost_label.configure(
            text=f"Est. Cost: ${cost:.4f} (~{tokens_str} tokens) - {desc}",
            text_color=AppColors.TEXT_SECONDARY
        )
    
    def update_status(self, message: str):
        """Update the status label and console with a message."""
        if self.preview_status:
            # Only update if message is short, otherwise keep current status
            if len(message) < 50:
                self.preview_status.configure(text=message)
        
        # Also write to console
        if hasattr(self, 'status_textbox') and self.status_textbox:
            self.status_textbox.configure(state="normal")
            self.status_textbox.insert("end", message + "\n")
            self.status_textbox.see("end")
            self.status_textbox.configure(state="disabled")
    
    def save_analysis_result(self, result, model_name: str):
        """
        Save an AI analysis result to history.
        
        Args:
            result: AnalysisResults object from analyze_content
            model_name: Display name of the model used (e.g., "Llama 3.3 70B")
        """
        if not result or not hasattr(result, 'decisions'):
            return
        
        # Calculate summary stats
        total = result.segments_analyzed
        keep_pct = (result.keep_count / total * 100) if total > 0 else 0
        
        # Create label with timestamp and summary
        timestamp = datetime.now().strftime("%I:%M %p")
        label = f"{timestamp} - {model_name} ({int(keep_pct)}% Keep)"
        
        # Store in history
        history_item = {
            "label": label,
            "result": result,
            "model_name": model_name,
            "timestamp": datetime.now()
        }
        
        self.analysis_history.append(history_item)
        
        # Update dropdown values
        values = [item["label"] for item in self.analysis_history]
        self.history_selector.configure(values=values, state="normal")
        self.history_var.set(label)  # Select the newest run
        
        self.update_status(f"💾 Saved analysis: {label}")
    
    def load_history_item(self, selected_label: str):
        """
        Load and restore a previous analysis result from history.
        
        Args:
            selected_label: The label of the history item to load
        """
        if not selected_label or selected_label == "No runs yet":
            return
        
        # Find the matching history item
        history_item = None
        for item in self.analysis_history:
            if item["label"] == selected_label:
                history_item = item
                break
        
        if not history_item:
            self.update_status("⚠️ Could not find history item")
            return
        
        result = history_item["result"]
        
        # Apply decisions to segments
        if self.detected_segments and result.decisions:
            try:
                updated_segments = apply_decisions_to_segments(
                    self.detected_segments.copy(),
                    result.decisions
                )
                self.detected_segments = updated_segments
                
                # Update timeline visualization
                if hasattr(self, 'preview_timeline') and self.preview_timeline:
                    # Get waveforms if available
                    waveforms = None
                    if hasattr(self.preview_timeline, 'waveforms'):
                        waveforms = self.preview_timeline.waveforms
                    
                    self.preview_timeline.update_timeline(
                        self.detected_segments,
                        self.duration,
                        waveforms
                    )
                
                # Update status
                self.update_status(f"✅ Restored: {selected_label}")
                self.preview_status.configure(
                    text=f"Restored: {history_item['model_name']} ({result.keep_count} Keep, {result.flag_count} Flag)"
                )
                
            except Exception as e:
                self.update_status(f"❌ Error restoring history: {str(e)}")
                messagebox.showerror("Restore Error", f"Failed to restore analysis:\n{str(e)}")
        else:
            self.update_status("⚠️ No segments or decisions to restore")
    
    def on_ai_analysis_complete(self, result, model_name: str):
        """
        Callback to be called when AI analysis completes.
        
        This method should be called after analyze_content() finishes successfully.
        It saves the result to history and applies it to the timeline.
        
        Example usage:
            from ..ai_analysis.orchestrator import analyze_content
            
            results = analyze_content(...)
            if results and not results.errors:
                self.on_ai_analysis_complete(results, "Llama 3.3 70B")
        
        Args:
            result: AnalysisResults object from analyze_content
            model_name: Display name of the model used
        """
        if not result or result.errors:
            self.update_status("⚠️ Analysis completed with errors - not saving to history")
            return
        
        # Save to history
        self.save_analysis_result(result, model_name)
        
        # Apply decisions immediately to current segments
        if self.detected_segments and result.decisions:
            try:
                updated_segments = apply_decisions_to_segments(
                    self.detected_segments.copy(),
                    result.decisions
                )
                self.detected_segments = updated_segments
                
                # Update timeline visualization
                if hasattr(self, 'preview_timeline') and self.preview_timeline:
                    waveforms = None
                    if hasattr(self.preview_timeline, 'waveforms'):
                        waveforms = self.preview_timeline.waveforms
                    
                    self.preview_timeline.update_timeline(
                        self.detected_segments,
                        self.duration,
                        waveforms
                    )
                
                self.update_status(f"✅ Analysis complete: {result.keep_count} Keep, {result.flag_count} Flag")
                
            except Exception as e:
                self.update_status(f"❌ Error applying decisions: {str(e)}")
                messagebox.showerror("Apply Error", f"Failed to apply AI decisions:\n{str(e)}")
