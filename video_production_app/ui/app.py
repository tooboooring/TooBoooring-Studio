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
        self.geometry("1280x800")
        self.minsize(1100, 700)
        
        # Set window icon if logo exists
        try:
            logo_path = Path(__file__).parent.parent.parent / "logo.png"
            if logo_path.exists():
                self.iconbitmap(str(logo_path))
                print(f"✅ Loaded app icon: {logo_path}")
        except Exception as e:
            print(f"⚠️ Could not load app icon: {e}")
        
        # Set appearance mode
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Center window on screen
        self._center_window()
        
        # Initialize application state
        self._initialize_state()
        
        # Set up FFmpeg paths
        self._setup_paths()
        
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
        base_path = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
        
        # Set FFmpeg paths
        self.ffmpeg_path = base_path / "ffmpeg.exe"
        self.ffprobe_path = base_path / "ffprobe.exe"
        self.ffplay_path = base_path / "ffplay.exe"
        
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
        
        This method sets up the tabbed interface and creates all the
        UI components. In the full implementation, this would import
        and set up each tab module.
        """
        # Configure main grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create main tab view
        self.tabview = ctk.CTkTabview(
            self, 
            corner_radius=15,
            border_width=2,
            border_color=AppColors.BORDER,
            segmented_button_fg_color=AppColors.BG_LIGHT,
            segmented_button_selected_color=AppColors.PRIMARY,
            segmented_button_selected_hover_color=AppColors.PRIMARY_HOVER,
            text_color=AppColors.TEXT_PRIMARY
        )
        self.tabview.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        
        # Add tabs - merged preview and main into one unified tab
        self.tab_editor = self.tabview.add("🎬 Video Editor")
        self.tab_advanced = self.tabview.add("Advanced Settings")
        self.tab_batch = self.tabview.add("Batch Queue")
        
        # Set up each tab
        self._setup_editor_tab()
        self._setup_advanced_tab()
        self._setup_batch_tab()
    
    def _setup_editor_tab(self):
        """
        Set up the unified video editor tab (merged preview + processing).
        
        This method creates the editor tab UI using the PreviewTab class,
        which now includes all preview and processing features.
        """
        # Import and create the editor tab (using PreviewTab with all features)
        from .preview_tab import PreviewTab
        
        self.editor_tab = PreviewTab(
            self.tab_editor,
            self.settings,
            self.ffmpeg_path,
            self.ffprobe_path,
            self.ffplay_path,
            on_video_loaded=self._on_preview_video_loaded,
            on_silence_detected=self._on_preview_silence_detected
        )
    
    def _setup_advanced_tab(self):
        """
        Set up the advanced settings tab.
        
        This method creates the advanced settings tab UI using the AdvancedTab class.
        """
        # Import and create the advanced tab
        from .advanced_tab import AdvancedTab
        
        self.advanced_tab = AdvancedTab(
            self.tab_advanced,
            self.settings,
            self._on_settings_change
        )
    
    def _setup_batch_tab(self):
        """
        Set up the batch processing tab.
        
        This method creates the batch processing tab UI using the BatchTab class.
        """
        # Import and create the batch tab
        from .batch_tab import BatchTab
        
        self.batch_tab = BatchTab(
            self.tab_batch,
            self.settings
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
