"""
Utility helper functions for Video Production App.

This module contains common utility functions used throughout the application.
These functions handle common tasks like time formatting, file operations,
and data validation.

Key functions:
- format_time: Convert seconds to human-readable time format
- format_duration: Format video duration for display
- validate_file_path: Check if file exists and is accessible
- get_file_size: Get human-readable file size
- sanitize_filename: Clean filename for safe saving
- load_icon: Load and cache icons from assets folder
"""

import os
from pathlib import Path
from typing import Optional, Union
from PIL import Image, ImageTk
import customtkinter as ctk
import tkinter as tk

# Icon cache to avoid reloading the same icons multiple times
ICON_CACHE = {}

def load_icon(name: str, size: int = 20):
    """
    Loads an icon from the assets folder and caches it.
    
    Args:
        name: Icon name without extension (e.g., "folder", "play", "pause")
        size: Icon size in pixels (default: 20)
        
    Returns:
        CTkImage object or None if icon not found
        
    Example:
        icon = load_icon("folder", 32)
        button.configure(image=icon, text="")
    """
    # Check cache first
    if (name, size) in ICON_CACHE:
        return ICON_CACHE[(name, size)]
    
    # Try to find icon in assets folder
    # Check multiple possible locations
    possible_paths = [
        os.path.join("assets", f"{name}.png"),
        os.path.join("video_production_app", "assets", f"{name}.png"),
        os.path.join(Path(__file__).parent.parent.parent, "assets", f"{name}.png"),
    ]
    
    icon_path = None
    for path in possible_paths:
        if os.path.exists(path):
            icon_path = path
            break
    
    if not icon_path:
        # Icon not found - return None (will use text fallback)
        print(f"Warning: Icon not found: {name}.png (searched: {possible_paths})")
        return None
    
    try:
        img = Image.open(icon_path)
        ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
        ICON_CACHE[(name, size)] = ctk_image
        return ctk_image
    except Exception as e:
        print(f"Error loading icon {name}: {e}")
        return None


class ToolTip:
    """
    Simple tooltip class for showing hover text on widgets.
    
    Usage:
        tooltip = ToolTip(button, "Load Video")
    """
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Motion>", self.on_motion)
    
    def on_enter(self, event=None):
        """Show tooltip when mouse enters widget."""
        self.schedule_tooltip()
    
    def on_leave(self, event=None):
        """Hide tooltip when mouse leaves widget."""
        self.hide_tooltip()
        if hasattr(self, 'tooltip_id'):
            self.widget.after_cancel(self.tooltip_id)
    
    def on_motion(self, event=None):
        """Update tooltip position when mouse moves."""
        if self.tooltip_window:
            self.update_position()
    
    def schedule_tooltip(self):
        """Schedule tooltip to appear after a short delay."""
        if hasattr(self, 'tooltip_id'):
            self.widget.after_cancel(self.tooltip_id)
        self.tooltip_id = self.widget.after(500, self.show_tooltip)  # 500ms delay
    
    def show_tooltip(self):
        """Show the tooltip window."""
        if self.tooltip_window:
            return
        
        # Get widget position
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.attributes("-topmost", True)
        
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            background="#2b2b2b",
            foreground="white",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9),
            padx=8,
            pady=4
        )
        label.pack()
        
        # Update position after window is created
        self.tooltip_window.update_idletasks()
        width = self.tooltip_window.winfo_width()
        x = self.widget.winfo_rootx() + (self.widget.winfo_width() // 2) - (width // 2)
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
    
    def update_position(self):
        """Update tooltip position."""
        if self.tooltip_window:
            width = self.tooltip_window.winfo_width()
            x = self.widget.winfo_rootx() + (self.widget.winfo_width() // 2) - (width // 2)
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
    
    def hide_tooltip(self):
        """Hide the tooltip window."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def add_tooltip(widget, text: str):
    """
    Add a tooltip to a widget.
    
    Args:
        widget: The widget to add tooltip to
        text: The tooltip text to display
        
    Example:
        add_tooltip(button, "Load Video File")
    """
    ToolTip(widget, text)


def format_time(seconds: float, include_milliseconds: bool = False) -> str:
    """
    Convert seconds to human-readable time format.
    
    This function takes a number of seconds and converts it to a readable
    format like "02:35.50" (2 minutes, 35 seconds, 50 centiseconds).
    
    Args:
        seconds: Time in seconds (can be decimal like 125.5)
        include_milliseconds: Whether to include milliseconds in output
        
    Returns:
        Formatted time string in MM:SS.CC format
        
    Examples:
        format_time(125.5)           # Returns "02:05.50"
        format_time(3661.25)         # Returns "61:01.25"
        format_time(30.0)            # Returns "00:30.00"
        format_time(125.5, True)     # Returns "02:05.500"
    """
    # Handle negative time (shouldn't happen, but be safe)
    if seconds < 0:
        seconds = 0
    
    # Split into minutes and seconds
    minutes = int(seconds // 60)  # Integer division to get whole minutes
    remaining_seconds = seconds % 60  # Remainder gives us seconds with decimals
    
    # Format the output string
    if include_milliseconds:
        # Include milliseconds (3 decimal places)
        return f"{minutes:02d}:{remaining_seconds:06.3f}"
    else:
        # Include centiseconds (2 decimal places) - standard for video timing
        return f"{minutes:02d}:{remaining_seconds:05.2f}"


def format_duration(total_seconds: float) -> str:
    """
    Format video duration for display in a user-friendly way.
    
    This function converts seconds to a more readable format that shows
    hours, minutes, and seconds as appropriate.
    
    Args:
        total_seconds: Duration in seconds
        
    Returns:
        Human-readable duration string
        
    Examples:
        format_duration(125.5)    # Returns "2m 5.5s"
        format_duration(3661.25) # Returns "1h 1m 1.25s"
        format_duration(30.0)    # Returns "30.0s"
    """
    if total_seconds < 0:
        return "0.0s"
    
    # Calculate hours, minutes, and seconds
    hours = int(total_seconds // 3600)  # 3600 seconds = 1 hour
    minutes = int((total_seconds % 3600) // 60)  # Remainder minutes
    seconds = total_seconds % 60  # Remainder seconds with decimals
    
    # Build the result string based on what we have
    parts = []
    
    if hours > 0:
        parts.append(f"{hours}h")
    
    if minutes > 0 or hours > 0:  # Show minutes if we have hours or minutes
        parts.append(f"{minutes}m")
    
    # Always show seconds (with appropriate decimal places)
    if seconds == int(seconds):  # If it's a whole number
        parts.append(f"{int(seconds)}s")
    else:
        parts.append(f"{seconds:.1f}s")
    
    return " ".join(parts)


def validate_file_path(file_path: Union[str, Path]) -> tuple[bool, str]:
    """
    Validate that a file path exists and is accessible.
    
    This function checks if a file exists and can be read, providing
    helpful error messages for common issues.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if file is valid, False otherwise
        - error_message: Empty string if valid, error description if invalid
        
    Examples:
        validate_file_path("video.mp4")     # Returns (True, "")
        validate_file_path("nonexistent")   # Returns (False, "File does not exist")
        validate_file_path("")              # Returns (False, "No file path provided")
    """
    # Convert to Path object for easier handling
    path = Path(file_path)
    
    # Check if path is empty
    if not file_path or not str(file_path).strip():
        return False, "No file path provided"
    
    # Check if file exists
    if not path.exists():
        return False, f"File does not exist: {path.name}"
    
    # Check if it's actually a file (not a directory)
    if not path.is_file():
        return False, f"Path is not a file: {path.name}"
    
    # Check if we can read the file
    try:
        with open(path, 'rb') as f:
            f.read(1)  # Try to read one byte
    except PermissionError:
        return False, f"Permission denied: {path.name}"
    except Exception as e:
        return False, f"Cannot read file: {str(e)}"
    
    # If we get here, file is valid
    return True, ""


def get_file_size(file_path: Union[str, Path]) -> str:
    """
    Get human-readable file size.
    
    This function converts file size in bytes to a more readable format
    using appropriate units (KB, MB, GB).
    
    Args:
        file_path: Path to the file
        
    Returns:
        Human-readable size string
        
    Examples:
        get_file_size("small.txt")    # Returns "1.2 KB"
        get_file_size("video.mp4")    # Returns "125.3 MB"
        get_file_size("large.mkv")    # Returns "2.1 GB"
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return "Unknown"
        
        size_bytes = path.stat().st_size
        
        # Define size units and their byte equivalents
        units = [
            ("B", 1),
            ("KB", 1024),
            ("MB", 1024 * 1024),
            ("GB", 1024 * 1024 * 1024),
            ("TB", 1024 * 1024 * 1024 * 1024)
        ]
        
        # Find the appropriate unit
        for unit_name, unit_size in reversed(units):
            if size_bytes >= unit_size:
                size_in_unit = size_bytes / unit_size
                # Format with appropriate decimal places
                if size_in_unit >= 100:
                    return f"{size_in_unit:.0f} {unit_name}"
                elif size_in_unit >= 10:
                    return f"{size_in_unit:.1f} {unit_name}"
                else:
                    return f"{size_in_unit:.2f} {unit_name}"
        
        # Fallback for very small files
        return f"{size_bytes} B"
        
    except Exception:
        return "Unknown"


def sanitize_filename(filename: str) -> str:
    """
    Clean filename to make it safe for saving.
    
    This function removes or replaces characters that could cause problems
    when saving files on different operating systems.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for saving
        
    Examples:
        sanitize_filename("video: with | pipes")  # Returns "video with pipes"
        sanitize_filename("file<>name")            # Returns "filename"
        sanitize_filename("normal_file.mp4")      # Returns "normal_file.mp4"
    """
    # Characters that are not allowed in filenames on most systems
    invalid_chars = '<>:"/\\|?*'
    
    # Replace invalid characters with underscores
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing spaces and dots (can cause issues)
    sanitized = sanitized.strip(' .')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = "untitled"
    
    # Limit length to prevent filesystem issues (255 chars is safe for most systems)
    if len(sanitized) > 255:
        # Keep the extension if it exists
        if '.' in sanitized:
            name, ext = sanitized.rsplit('.', 1)
            # Truncate name part, keep extension
            max_name_length = 255 - len(ext) - 1  # -1 for the dot
            sanitized = name[:max_name_length] + '.' + ext
        else:
            sanitized = sanitized[:255]
    
    return sanitized


def get_relative_time(current_time: float, total_duration: float) -> str:
    """
    Get relative time position as a percentage.
    
    This function calculates what percentage of the video we're currently at,
    useful for progress bars and status displays.
    
    Args:
        current_time: Current position in seconds
        total_duration: Total duration in seconds
        
    Returns:
        Percentage string with % symbol
        
    Examples:
        get_relative_time(30, 120)    # Returns "25.0%"
        get_relative_time(0, 100)     # Returns "0.0%"
        get_relative_time(100, 100)   # Returns "100.0%"
    """
    if total_duration <= 0:
        return "0.0%"
    
    percentage = (current_time / total_duration) * 100
    # Cap at 100% to avoid showing more than complete
    percentage = min(100.0, percentage)
    
    return f"{percentage:.1f}%"


def format_bitrate(bitrate_bps: int) -> str:
    """
    Format bitrate from bits per second to human-readable format.
    
    This function converts raw bitrate values to more readable formats
    like "128 kbps" or "2.5 Mbps".
    
    Args:
        bitrate_bps: Bitrate in bits per second
        
    Returns:
        Formatted bitrate string
        
    Examples:
        format_bitrate(128000)      # Returns "128 kbps"
        format_bitrate(2500000)     # Returns "2.5 Mbps"
        format_bitrate(1000000000)  # Returns "1.0 Gbps"
    """
    if bitrate_bps <= 0:
        return "Unknown"
    
    # Convert to appropriate units
    if bitrate_bps >= 1_000_000_000:  # Gigabits per second
        return f"{bitrate_bps / 1_000_000_000:.1f} Gbps"
    elif bitrate_bps >= 1_000_000:  # Megabits per second
        return f"{bitrate_bps / 1_000_000:.1f} Mbps"
    elif bitrate_bps >= 1_000:  # Kilobits per second
        return f"{bitrate_bps / 1_000:.0f} kbps"
    else:  # Bits per second
        return f"{bitrate_bps} bps"
