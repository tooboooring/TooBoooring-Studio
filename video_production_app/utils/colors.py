"""
Color theme and styling constants for Video Production App.

This module defines the complete color scheme used throughout the application.
The colors are carefully chosen to provide a professional, modern appearance
with good contrast and accessibility.

The color scheme includes:
- Primary colors: Main brand colors for buttons and highlights
- Accent colors: Status indicators (success, warning, error, info)
- Background colors: Different levels of background for visual hierarchy
- Text colors: Various text colors for different importance levels
- Border colors: Subtle borders for visual separation
- Special colors: Timeline segments, waveform colors, etc.

All colors are defined as hex strings that work with CustomTkinter widgets.
"""


class AppColors:
    """
    Professional color scheme for the Video Production App.
    
    This class contains all the colors used throughout the application,
    organized by purpose. Colors are defined as class attributes so they
    can be easily accessed and modified.
    
    Color naming convention:
    - PRIMARY: Main brand color (blue theme)
    - SUCCESS: Green for successful operations
    - WARNING: Amber/yellow for warnings
    - DANGER: Red for errors
    - INFO: Light blue for informational messages
    - BG_: Background colors (dark theme)
    - TEXT_: Text colors for different contexts
    - BORDER_: Border colors for visual separation
    
    Example usage:
        button.configure(fg_color=AppColors.PRIMARY)
        label.configure(text_color=AppColors.TEXT_PRIMARY)
    """
    
    # === PRIMARY COLORS ===
    # Main brand color - used for primary buttons, highlights, and accents
    PRIMARY = "#1f6aa5"  # Professional blue
    PRIMARY_HOVER = "#1a5a8f"  # Darker blue for hover effects
    PRIMARY_DARK = "#164a75"  # Even darker blue for pressed states
    
    # === ACCENT COLORS ===
    # Status indicators for different types of messages
    SUCCESS = "#2fb344"  # Green - for successful operations (file saved, processing complete)
    SUCCESS_HOVER = "#25a339"  # Darker green for hover effects
    
    WARNING = "#f59e0b"  # Amber - for warnings (missing files, low disk space)
    DANGER = "#ef4444"  # Red - for errors (processing failed, invalid input)
    INFO = "#3b82f6"  # Light blue - for informational messages
    
    # === BACKGROUND COLORS ===
    # Different levels of background for visual hierarchy
    # Darker backgrounds are used for main areas, lighter for cards/panels
    BG_DARK = "#1E1E1E"  # Main application background
    BG_MEDIUM = "#2B2B2B"  # Secondary background (panels, cards)
    BG_LIGHT = "#383838"  # Light background (hover states, active elements, panel headers)
    BG_CARD = "#2B2B2B"  # Card background
    BG_CARD_HOVER = "#383838"  # Card hover background
    
    # === TEXT COLORS ===
    # Different text colors for different importance levels
    TEXT_PRIMARY = "#CCCCCC"  # Main text color - highest contrast (matching web UI)
    TEXT_SECONDARY = "#888888"  # Secondary text - medium importance (matching web UI)
    TEXT_MUTED = "#666666"  # Muted text - low importance (hints, labels)
    
    # === BORDER COLORS ===
    # Subtle borders for visual separation between elements
    BORDER = "#444444"  # Standard border color (matching web UI)
    BORDER_LIGHT = "#555555"  # Lighter border for subtle separation
    
    # === TIMELINE SEGMENT COLORS ===
    # Colors for the interactive timeline visualization
    SEGMENT_KEEP = "#2fb344"  # Green - segments that will be kept in final video
    SEGMENT_REMOVE = "#2b2b2b"  # Dark gray - segments that will be removed (silence)
    SEGMENT_BORDER = "#25a339"  # Darker green - borders around kept segments
    
    # === WAVEFORM COLORS ===
    # Different colors for multiple audio tracks in waveform visualization
    # Each track gets a different color so they can be distinguished
    WAVEFORM_COLORS = [
        "#3b82f6",  # Blue - Track 1
        "#10b981",  # Emerald - Track 2
        "#f59e0b",  # Amber - Track 3
        "#ec4899",  # Pink - Track 4
        "#8b5cf6",  # Violet - Track 5
        "#06b6d4",  # Cyan - Track 6
    ]
    
    @classmethod
    def get_waveform_color(cls, track_index: int) -> str:
        """
        Get the color for a specific audio track in waveform visualization.
        
        Args:
            track_index: The index of the audio track (0-based)
            
        Returns:
            Hex color string for the track
            
        Example:
            color = AppColors.get_waveform_color(0)  # Returns "#3b82f6" (blue)
            color = AppColors.get_waveform_color(3)  # Returns "#ec4899" (pink)
        """
        # Use modulo to cycle through colors if there are more tracks than colors
        return cls.WAVEFORM_COLORS[track_index % len(cls.WAVEFORM_COLORS)]
    
    @classmethod
    def get_status_color(cls, status: str) -> str:
        """
        Get the appropriate color for a given status.
        
        Args:
            status: Status string ("success", "warning", "error", "info")
            
        Returns:
            Hex color string for the status
            
        Example:
            color = AppColors.get_status_color("success")  # Returns "#2fb344"
            color = AppColors.get_status_color("error")    # Returns "#ef4444"
        """
        status_colors = {
            "success": cls.SUCCESS,
            "warning": cls.WARNING,
            "error": cls.DANGER,
            "info": cls.INFO,
            "pending": cls.TEXT_SECONDARY,
            "processing": cls.PRIMARY,
            "completed": cls.SUCCESS,
            "failed": cls.DANGER
        }
        return status_colors.get(status.lower(), cls.TEXT_PRIMARY)
