"""
Main application window for Video Production App v3.

This module contains the main application class that coordinates all the
UI components and manages the overall application state. It's been refactored
from the original monolithic file into a clean, organized structure.

Key features:
- Tab-based interface with separate modules for each tab
- Settings management and persistence
- State coordination between components
- Error handling and user feedback

The VideoProductionApp class serves as the main coordinator, importing
and managing all the individual tab modules and widgets.
"""

import sys
from pathlib import Path
from typing import Optional

import customtkinter as ctk

# Import our refactored modules
from ..core.settings_manager import SettingsManager
from ..core.ffmpeg_wrapper import get_available_encoders
from ..utils.colors import AppColors
from ..utils.helpers import format_time, validate_file_path


class VideoProductionApp(ctk.CTk):
    """
    Main application window for Video Production App v3.
    
    This class serves as the main coordinator for the entire application.
    It manages the tabbed interface, settings, and communication between
    different components.
    
    Key responsibilities:
    - Initialize the main window and UI
    - Manage application settings
    - Coordinate between different tabs
    - Handle file operations and state management
    - Provide status updates and error handling
    
    Attributes:
        settings: SettingsManager instance for persistent settings
        video_path: Path to currently loaded video file
        save_path: Directory for saving processed videos
        ffmpeg_path: Path to FFmpeg executable
        ffprobe_path: Path to FFprobe executable
        ffplay_path: Path to FFplay executable
        available_tracks: List of detected audio tracks
        detected_segments: List of detected silence segments
        current_duration: Duration of current video
        batch_queue: List of videos in batch processing queue
        processing: Whether video processing is currently active
        
    Example usage:
        app = VideoProductionApp()
        app.mainloop()
    """
    
    def __init__(self):
        """
        Initialize the main application window.
        
        This constructor sets up the main window, initializes all components,
        and creates the tabbed interface. It also loads settings and sets up
        the initial state.
        """
        super().__init__()
        
        # Set window properties
        self.title("🎬 Video Production Suite v3.0 - Professional Edition")
        
        # Set appearance mode (matching web UI)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Override default colors to match web UI exactly
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)
        
        # Set window size (don't auto-fullscreen, let user control)
        self.geometry("1920x1080")
        self._center_window()
        
        # Set minimum size
        self.minsize(1100, 700)
        
        # Set window icon if logo exists
        try:
            logo_path = Path(__file__).parent.parent.parent / "logo.png"
            if logo_path.exists():
                self.iconbitmap(str(logo_path))
                print(f"✅ Loaded app icon: {logo_path}")
        except Exception as e:
            print(f"⚠️ Could not load app icon: {e}")
        
        # Initialize application state
        self._initialize_state()
        
        # Set up FFmpeg paths
        self._setup_paths()
        
        # Detect available encoders once at startup
        self.available_encoders = get_available_encoders(self.ffmpeg_path, self.update_status)
        if not self.available_encoders:
            # Fallback to CPU encoder if detection fails
            self.available_encoders = ["CPU (x264)"]
        
        # Initialize settings manager
        self.settings = SettingsManager()
        
        # Create the user interface
        self._create_ui()
        
        # Show initial status
        self._show_initial_status()
    
    def _center_window(self):
        """
        Center the application window on the screen.
        
        This method calculates the screen dimensions and positions the
        window in the center of the screen.
        """
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 1280) // 2
        y = (screen_height - 800) // 2
        self.geometry(f"1280x800+{x}+{y}")
    
    def _initialize_state(self):
        """
        Initialize all application state variables.
        
        This method sets up all the instance variables that track
        the current state of the application.
        """
        # File paths
        self.video_path = ""
        self.save_path = ""
        
        # FFmpeg executable paths
        self.ffmpeg_path = ""
        self.ffprobe_path = ""
        self.ffplay_path = ""
        
        # Video information
        self.available_tracks = []
        self.detected_segments = []
        self.current_duration = 0
        
        # Processing state
        self.batch_queue = []
        self.processing = False
    
    def _setup_paths(self):
        """
        Set up FFmpeg executable paths.
        
        This method looks for FFmpeg executables in the application
        directory and falls back to system PATH if not found.
        """
        # Determine base path (works for both frozen and development)
        base_path = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent
        
        # Set FFmpeg paths (now in bin/ folder)
        bin_path = base_path / "bin"
        self.ffmpeg_path = bin_path / "ffmpeg.exe"
        self.ffprobe_path = bin_path / "ffprobe.exe"
        self.ffplay_path = bin_path / "ffplay.exe"
        
        # Check if files exist, fall back to empty string for system PATH
        if not self.ffmpeg_path.exists():
            self.ffmpeg_path = ""
        if not self.ffprobe_path.exists():
            self.ffprobe_path = ""
        if not self.ffplay_path.exists():
            self.ffplay_path = ""
    
    def _create_ui(self):
        """
        Create the main user interface.
        
        This method sets up the main editor interface with corner buttons
        for Advanced and Batch Queue instead of tabs.
        """
        # Configure main grid - no padding, full utilization
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main editor container (no borders, no padding)
        self.editor_container = ctk.CTkFrame(
            self,
            fg_color=AppColors.BG_DARK,
            border_width=0,
            corner_radius=0
        )
        self.editor_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.editor_container.grid_columnconfigure(0, weight=1)
        self.editor_container.grid_rowconfigure(0, weight=1)
        
        # Set up editor tab
        self._setup_editor_tab()
    
    def _setup_editor_tab(self):
        """
        Set up the unified video editor tab (merged preview + processing).
        
        This method creates the editor tab UI using the PreviewTab class,
        which now includes all preview and processing features.
        """
        # Import and create the editor tab (using PreviewTab with all features)
        from .preview_tab import PreviewTab
        
        self.editor_tab = PreviewTab(
            self.editor_container,
            self.settings,
            self.ffmpeg_path,
            self.ffprobe_path,
            self.ffplay_path,
            available_encoders=self.available_encoders,
            on_video_loaded=self._on_preview_video_loaded,
            on_silence_detected=self._on_preview_silence_detected
        )
    
    def _show_initial_status(self):
        """
        Show initial application status.
        
        This method displays the initial status information to the user,
        including FFmpeg availability and any warnings.
        """
        # In the full implementation, this would show status in a status bar
        print("Video Production App v3.0 initialized")
        print(f"FFmpeg path: {self.ffmpeg_path or 'System PATH'}")
        print(f"FFprobe path: {self.ffprobe_path or 'System PATH'}")
        print(f"FFplay path: {self.ffplay_path or 'System PATH'}")
    
    def update_status(self, message: str):
        """
        Update status message for the user.
        
        This method provides a way for other components to update
        the status display. In the full implementation, this would
        update a status bar or log area.
        
        Args:
            message: Status message to display
            
        Example:
            app.update_status("Processing video...")
        """
        # In the full implementation, this would update a status widget
        print(f"Status: {message.strip()}")
    
    def update_progress(self, percentage: float, eta: str, speed: float):
        """
        Update progress information for the user.
        
        This method provides a way for processing components to update
        progress information. In the full implementation, this would
        update a progress bar and ETA display.
        
        Args:
            percentage: Progress percentage (0-100)
            eta: Estimated time remaining
            speed: Processing speed multiplier
            
        Example:
            app.update_progress(45.5, "00:02:30", 2.1)
        """
        # In the full implementation, this would update progress widgets
        print(f"Progress: {percentage:.1f}% - ETA: {eta} - Speed: {speed:.1f}x")
    
    def load_video(self, video_path: str) -> bool:
        """
        Load a video file for processing.
        
        This method loads a video file and extracts information about
        it, including audio tracks and duration. It validates the file
        and updates the application state.
        
        Args:
            video_path: Path to the video file to load
            
        Returns:
            True if video loaded successfully, False otherwise
            
        Example:
            success = app.load_video("video.mp4")
            if success:
                print("Video loaded successfully")
        """
        # Validate file path
        is_valid, error_msg = validate_file_path(video_path)
        if not is_valid:
            self.update_status(f"Error loading video: {error_msg}")
            return False
        
        # Set video path
        self.video_path = video_path
        
        # In the full implementation, this would:
        # - Load video with FFprobe
        # - Detect audio tracks
        # - Get video duration
        # - Update UI components
        
        self.update_status(f"Video loaded: {Path(video_path).name}")
        return True
    
    def save_settings(self):
        """
        Save current settings to file.
        
        This method saves all current settings to the settings file
        for persistence between application runs.
        """
        self.settings.save_settings()
        self.update_status("Settings saved")
    
    def _on_settings_change(self):
        """
        Handle settings changes from the advanced tab.
        
        This method is called when settings are changed in the advanced tab
        and can be used to update other parts of the application.
        """
        # In the full implementation, this would update other tabs
        # that depend on the settings
        pass
    
    def _on_preview_video_loaded(self, video_path: str, duration: float, audio_tracks: list):
        """
        Handle video loaded in editor tab.
        
        This method is called when a video is loaded in the editor tab.
        It updates the app state.
        
        Args:
            video_path: Path to the loaded video file
            duration: Duration of the video in seconds
            audio_tracks: List of audio track information
        """
        # Update app state
        self.video_path = video_path
        self.current_duration = duration
        self.available_tracks = audio_tracks
    
    def _on_preview_silence_detected(self, segments: list, track_index: int):
        """
        Handle silence detection completed in editor tab.
        
        This method is called when silence detection is completed in the editor tab.
        It updates the app state.
        
        Args:
            segments: List of detected silence segments
            track_index: Index of the track that was analyzed
        """
        # Update app state
        self.detected_segments = segments
    
    def cleanup(self):
        """
        Clean up resources when application is closing.
        
        This method should be called when the application is closing
        to clean up any resources and save settings.
        """
        # Save settings
        self.save_settings()
        
        # Clean up any other resources
        self.update_status("Application closing...")
