"""
Interactive timeline widget for Video Production App.

This module provides an interactive timeline widget that displays video duration,
waveform visualization, and silence segments. This is an exact copy of the original
InteractiveTimeline class from Video_production_app_v3.py with only comments added.

Key features:
- Click-to-navigate timeline
- Waveform visualization for multiple audio tracks
- Silence segment visualization
- Playhead indicator
- Time scale display
"""

import customtkinter as ctk
from tkinter import Canvas
from typing import Optional, List, Tuple, Callable, Dict, Any
from datetime import timedelta

# Optional import for numpy - handle case where it's not installed
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("[WARNING] numpy not installed. Waveform visualization will be limited.")

from .waveform import WaveformGenerator
from ...utils.colors import AppColors


class InteractiveTimeline(ctk.CTkFrame):
    """
    Interactive timeline with waveform visualization.
    Click to navigate, drag playhead, show segments.
    
    This class is an exact copy from the original Video_production_app_v3.py file.
    It provides multi-track waveform visualization with click-to-navigate functionality.
    """
    
    def __init__(self, master, on_time_click=None, **kwargs):
        """
        Initialize the interactive timeline widget.
        
        Args:
            master: Parent widget
            on_time_click: Optional callback function called when timeline is clicked
            **kwargs: Additional arguments passed to CTkFrame
        """
        super().__init__(master, **kwargs)
        
        # Timeline state variables
        self.segments = []  # List of dicts: {'start': float, 'end': float, 'type': 'audible'|'silent', 'keep': bool}
        self.duration = 0   # Total duration of the video in seconds
        self.waveforms = {}  # Dict of track_index -> waveform data
        self.playhead_time = 0  # Current playhead position in seconds
        self.on_time_click = on_time_click  # Callback function for timeline clicks
        self.dragging = False  # Flag to track if user is dragging the playhead
        
        # Zoom state variables
        self.zoom_level = 1.0  # Current zoom level (1.0 = full view)
        self.view_start = 0.0  # Start time of visible area in seconds
        self.view_end = 0.0    # End time of visible area in seconds
        # Initialize view_end to duration when duration is set (anchored to right)
        self.min_zoom = 0.1    # Minimum zoom level (10x zoom out)
        self.max_zoom = 100.0  # Maximum zoom level (100x zoom in for frame-accurate editing)
        
        # Set up the user interface
        self.setup_ui()
    
    def setup_ui(self):
        """
        Setup timeline UI exactly as in the original file.
        Creates the header, time ruler, waveform display, and segments display.
        """
        # Header section with title, zoom controls, and info label
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        # Timeline title
        ctk.CTkLabel(header, text="📊 Interactive Timeline", 
                    font=("", 14, "bold")).pack(side="left")
        
        # Zoom controls in the middle
        zoom_frame = ctk.CTkFrame(header, fg_color="transparent")
        zoom_frame.pack(side="left", padx=20)
        
        # Zoom out button
        zoom_out_btn = ctk.CTkButton(
            zoom_frame, 
            text="🔍-", 
            width=30, 
            height=25,
            command=self.zoom_out,
            font=("", 12, "bold")
        )
        zoom_out_btn.pack(side="left", padx=2)
        
        # Zoom level display
        self.zoom_label = ctk.CTkLabel(
            zoom_frame, 
            text="100%", 
            width=50,
            font=("", 10, "bold")
        )
        self.zoom_label.pack(side="left", padx=5)
        
        # Zoom in button
        zoom_in_btn = ctk.CTkButton(
            zoom_frame, 
            text="🔍+", 
            width=30, 
            height=25,
            command=self.zoom_in,
            font=("", 12, "bold")
        )
        zoom_in_btn.pack(side="left", padx=2)
        
        # Reset zoom button
        reset_zoom_btn = ctk.CTkButton(
            zoom_frame, 
            text="🏠", 
            width=30, 
            height=25,
            command=self.reset_zoom,
            font=("", 12, "bold")
        )
        reset_zoom_btn.pack(side="left", padx=2)
        
        # Scroll controls
        scroll_frame = ctk.CTkFrame(header, fg_color="transparent")
        scroll_frame.pack(side="left", padx=20)
        
        # Scroll left button
        scroll_left_btn = ctk.CTkButton(
            scroll_frame, 
            text="◀", 
            width=30, 
            height=25,
            command=self.scroll_left,
            font=("", 12, "bold")
        )
        scroll_left_btn.pack(side="left", padx=2)
        
        # Scroll right button
        scroll_right_btn = ctk.CTkButton(
            scroll_frame, 
            text="▶", 
            width=30, 
            height=25,
            command=self.scroll_right,
            font=("", 12, "bold")
        )
        scroll_right_btn.pack(side="left", padx=2)
        
        # Info label showing track count and processing stats
        self.info_label = ctk.CTkLabel(header, text="Load video and detect silence",
                                       font=("", 10))
        self.info_label.pack(side="right")
        
        # Create scrollable frame for timeline content (horizontal scrolling only)
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=AppColors.PRIMARY,
            scrollbar_button_hover_color=AppColors.PRIMARY_HOVER,
            orientation="horizontal"
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=(0, 2))
        
        # Initial canvas width (will be updated based on zoom level)
        initial_canvas_width = 800
        
        # Time ruler canvas - shows time markers at the top
        self.ruler_canvas = Canvas(self.scrollable_frame, bg="gray25", height=25, highlightthickness=0, width=initial_canvas_width)
        self.ruler_canvas.pack(fill="x", pady=(0, 2))
        
        # Waveform display container - holds the multi-track waveform visualization
        waveform_container = ctk.CTkFrame(self.scrollable_frame, fg_color="gray20", height=80)
        waveform_container.pack(fill="x", pady=0)
        waveform_container.pack_propagate(False)  # Prevent container from shrinking

        # Waveform canvas - where the actual waveforms are drawn
        self.waveform_canvas = Canvas(waveform_container, bg="#1a1a1a", 
                                      highlightthickness=0, width=initial_canvas_width)
        self.waveform_canvas.pack(fill="both", expand=True, padx=5, pady=5)

        # Segments display container - shows which parts will be kept/removed (same height as waveform)
        segments_container = ctk.CTkFrame(self.scrollable_frame, fg_color="gray20", height=80)
        segments_container.pack(fill="x", pady=(2, 0))
        segments_container.pack_propagate(False)  # Prevent container from shrinking
        
        # Segments canvas - where the segment visualization is drawn
        self.segments_canvas = Canvas(segments_container, bg="#1a1a1a",
                                      highlightthickness=0, width=initial_canvas_width)
        self.segments_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Bind mouse events for interaction on both canvases
        # This allows users to click and drag to navigate the timeline
        self.waveform_canvas.bind("<Button-1>", self.on_canvas_click)
        self.waveform_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.waveform_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        self.segments_canvas.bind("<Button-1>", self.on_segment_click)
        self.segments_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.segments_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # Bind mouse wheel events for zooming
        self.waveform_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.segments_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.ruler_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        
        # Bind mouse wheel events for Linux (Button-4/5)
        self.waveform_canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.waveform_canvas.bind("<Button-5>", self.on_mouse_wheel)
        self.segments_canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.segments_canvas.bind("<Button-5>", self.on_mouse_wheel)
        self.ruler_canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.ruler_canvas.bind("<Button-5>", self.on_mouse_wheel)
        
        # Bind horizontal scrolling (Shift + Mouse Wheel)
        self.waveform_canvas.bind("<Shift-MouseWheel>", self.on_horizontal_scroll)
        self.segments_canvas.bind("<Shift-MouseWheel>", self.on_horizontal_scroll)
        self.ruler_canvas.bind("<Shift-MouseWheel>", self.on_horizontal_scroll)
        
        # Bind keyboard arrow keys for scrolling
        self.waveform_canvas.bind("<KeyPress>", self.on_key_press)
        self.segments_canvas.bind("<KeyPress>", self.on_key_press)
        self.ruler_canvas.bind("<KeyPress>", self.on_key_press)
        
        # Make canvases focusable for keyboard events
        self.waveform_canvas.focus_set()
        self.segments_canvas.focus_set()
        self.ruler_canvas.focus_set()
    
    def update_timeline(self, segments: List[Dict[str, Any]], duration: float,
                       waveforms: dict = None):
        """
        Update timeline with segments and multi-track waveforms.
        
        Args:
            segments: List of dicts with 'start', 'end', 'type', 'keep' keys
            duration: Total duration of the video in seconds
            waveforms: Dictionary mapping track indices to waveform data
        """
        # Store the new data
        self.segments = segments
        self.duration = duration
        self.waveforms = waveforms if waveforms is not None else {}
        self.playhead_time = 0  # Reset playhead to beginning
        
        # Initialize zoom state
        self.zoom_level = 1.0
        self.view_start = 0.0
        self.view_end = duration
        
        # Don't draw if no valid data
        if not segments or duration == 0:
            return
        
        # Draw the complete timeline
        self.draw_timeline()
        
        # Update the info label with statistics
        num_tracks = len(self.waveforms)
        # Calculate total audible time (segments with type='audible' and keep=True)
        total_audible = sum(seg['end'] - seg['start'] for seg in segments 
                           if seg.get('type') == 'audible' and seg.get('keep', True))
        total_silence = duration - total_audible  # Total time that will be removed
        percent_kept = (total_audible / duration * 100) if duration > 0 else 0
        
        # Format the info text with track count and timing information
        self.info_label.configure(
            text=f"Tracks: {num_tracks} | Keep: {timedelta(seconds=int(total_audible))} | "
                 f"Remove: {timedelta(seconds=int(total_silence))} | "
                 f"{percent_kept:.1f}% retained"
        )
    
    def update_statistics(self):
        """
        Update the statistics info label based on current segment keep status.
        
        This method recalculates the total audible time and updates the info label
        to reflect any changes made by toggling silence segments.
        """
        if not self.segments or self.duration == 0:
            return
        
        num_tracks = len(self.waveforms)
        
        # Calculate total audible time (segments with type='audible' and keep=True)
        # Plus any silent segments that have been marked to keep
        total_keep = sum(
            seg['end'] - seg['start'] 
            for seg in self.segments 
            if seg.get('keep', True)
        )
        
        total_remove = self.duration - total_keep
        percent_kept = (total_keep / self.duration * 100) if self.duration > 0 else 0
        
        # Update the info label
        self.info_label.configure(
            text=f"Tracks: {num_tracks} | Keep: {timedelta(seconds=int(total_keep))} | "
                 f"Remove: {timedelta(seconds=int(total_remove))} | "
                 f"{percent_kept:.1f}% retained"
        )
    
    def draw_timeline(self):
        """
        Draw complete timeline with waveform and segments.
        This is the main drawing method that coordinates all the visual elements.
        """
        if self.duration == 0:
            return
        
        # Clear all canvases to start fresh
        self.ruler_canvas.delete("all")
        self.waveform_canvas.delete("all")
        self.segments_canvas.delete("all")
        
        # Calculate canvas width based on widget width and zoom level
        # This makes the canvases wider when zoomed in, enabling horizontal scrolling
        widget_width = self.winfo_width() or 800  # Fallback to 800 if not yet rendered
        canvas_width = int(widget_width * self.zoom_level)
        canvas_width = max(800, min(canvas_width, 50000))  # Clamp between 800 and 50000
        
        # Update canvas widths for horizontal scrolling
        self.ruler_canvas.configure(width=canvas_width)
        self.waveform_canvas.configure(width=canvas_width)
        self.segments_canvas.configure(width=canvas_width)
        
        # Get canvas dimensions
        ruler_width = canvas_width
        wave_width = canvas_width
        wave_height = self.waveform_canvas.winfo_height() or 80
        seg_width = canvas_width
        seg_height = 80  # Match waveform height
        
        # Calculate visible time range based on zoom
        # When zoomed out (zoom_level <= 1.0), always draw full timeline to anchor to right
        # When zoomed in (zoom_level > 1.0), draw only visible area
        if self.zoom_level <= 1.0:
            # Draw full timeline when zoomed out - this ensures right side stays anchored
            draw_start = 0.0
            draw_end = self.duration
            visible_duration = self.duration
        else:
            # Draw visible area when zoomed in
            draw_start = self.view_start
            draw_end = self.view_end
            visible_duration = self.view_end - self.view_start
        
        # Draw each section of the timeline with zoom support
        self.draw_ruler(ruler_width, visible_duration, draw_start, draw_end)  # Time markers at the top
        
        # Draw waveforms (multiple tracks) if available
        if self.waveforms:
            self.draw_multi_waveforms(wave_width, wave_height, visible_duration, draw_start, draw_end)
        
        # Draw segments (green = keep, dark = remove)
        self.draw_segments(seg_width, seg_height, visible_duration, draw_start, draw_end)
        
        # Draw playhead (red line showing current position)
        self.draw_playhead(wave_width, wave_height, seg_width, seg_height, visible_duration, draw_start, draw_end)
    
    def draw_ruler(self, width, visible_duration, draw_start=0.0, draw_end=None):
        """
        Draw time ruler with markers and labels, supporting zoom.
        
        Args:
            width: Width of the ruler canvas
            visible_duration: Duration of the visible area in seconds
            draw_start: Start time to draw from (default: 0.0)
            draw_end: End time to draw to (default: duration)
        """
        if draw_end is None:
            draw_end = self.duration
        
        # Fill the ruler background
        self.ruler_canvas.create_rectangle(0, 0, width, 25, fill="gray25", outline="")
        
        # Determine appropriate time interval based on visible duration
        if visible_duration <= 10:      # Very zoomed in: 0.1 second intervals
            interval = 0.1
        elif visible_duration <= 60:   # Less than 1 minute: 1 second intervals
            interval = 1
        elif visible_duration <= 300:  # Less than 5 minutes: 5 second intervals
            interval = 5
        elif visible_duration <= 1800: # Less than 30 minutes: 30 second intervals
            interval = 30
        elif visible_duration <= 3600:  # Less than 1 hour: 1 minute intervals
            interval = 60
        else:                           # More than 1 hour: 5 minute intervals
            interval = 300
        
        # Calculate how many intervals we need for the visible area
        num_intervals = int(visible_duration / interval) + 1
        
        # Draw each time marker
        for i in range(num_intervals):
            time_sec = draw_start + (i * interval)
            if time_sec > draw_end:
                break
            
            # Calculate x position for this time marker (relative to draw area)
            x = ((time_sec - draw_start) / visible_duration) * width
            
            # Format time as hours:minutes:seconds or minutes:seconds
            hours = int(time_sec // 3600)
            minutes = int((time_sec % 3600) // 60)
            seconds = int(time_sec % 60)
            
            if hours > 0:
                time_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            elif visible_duration <= 60:  # Show seconds for short durations
                time_str = f"{seconds}.{int((time_sec % 1) * 10)}"
            else:
                time_str = f"{minutes}:{seconds:02d}"
            
            # Draw tick mark (taller every 5th marker)
            tick_height = 15 if i % 5 == 0 else 10
            self.ruler_canvas.create_line(x, 25 - tick_height, x, 25,
                                         fill="white", width=1)
            
            # Draw time label (only on major markers or if few intervals)
            if i % 5 == 0 or num_intervals <= 10:
                self.ruler_canvas.create_text(x, 5, text=time_str, fill="white",
                                             font=("", 8), anchor="n")
    
    def draw_multi_waveforms(self, width, height, visible_duration, draw_start=0.0, draw_end=None):
        """
        Draw multiple audio waveforms stacked vertically, supporting zoom.
        Each track gets its own color and is separated by a line.
        
        Args:
            width: Width of the waveform canvas
            height: Height of the waveform canvas
            visible_duration: Duration of the visible area in seconds
            draw_start: Start time to draw from (default: 0.0)
            draw_end: End time to draw to (default: duration)
        """
        if draw_end is None:
            draw_end = self.duration
        
        if not self.waveforms or not NUMPY_AVAILABLE:
            return
        
        # Different colors for each track (bright and dim versions)
        track_colors = ["#4a9eff", "#ff6b6b", "#51cf66", "#ffd43b", "#ff8c00", "#ba68c8"]
        track_colors_dim = ["#2d5f99", "#993f3f", "#307a3d", "#997a23", "#99540a", "#6d3e75"]
        
        # Calculate how much height each track gets
        num_tracks = len(self.waveforms)
        track_height = height / num_tracks
        
        # Sort tracks by index for consistent display order
        sorted_tracks = sorted(self.waveforms.items())
        
        # Draw each track
        for idx, (track_index, waveform_data) in enumerate(sorted_tracks):
            waveform = waveform_data["waveform"]
            track_info = waveform_data["track_info"]
            
            # Downsample waveform to fit the display width (only visible portion)
            # Calculate which portion of the waveform to display based on draw area
            waveform_start_idx = int((draw_start / self.duration) * len(waveform))
            waveform_end_idx = int((draw_end / self.duration) * len(waveform))
            
            # Extract the visible portion of the waveform
            visible_waveform = waveform[waveform_start_idx:waveform_end_idx]
            
            # Downsample the visible portion to fit the display width
            downsampled = WaveformGenerator.downsample_waveform(visible_waveform, width)
            
            # Normalize the waveform to use full height
            if len(downsampled) > 0:
                max_val = np.max(np.abs(downsampled))
                if max_val > 0:
                    downsampled = downsampled / max_val
            
            # Calculate vertical position for this track
            track_y_start = idx * track_height
            track_center_y = track_y_start + track_height / 2
            
            # Get colors for this track
            color_idx = idx % len(track_colors)
            active_color = track_colors[color_idx]    # Bright color for audible parts
            dim_color = track_colors_dim[color_idx]  # Dim color for silent parts
            
            # Draw separator line between tracks (except for first track)
            if idx > 0:
                self.waveform_canvas.create_line(0, track_y_start, width, track_y_start,
                                                fill="#333333", width=1)
            
            # Draw track label
            label_text = f"Track {track_index + 1}"
            self.waveform_canvas.create_text(5, track_y_start + 5, text=label_text,
                                            anchor="nw", fill="white", font=("", 8, "bold"))
            
            # Draw the actual waveform
            for i, val in enumerate(downsampled):
                # Calculate amplitude (height) of this sample
                amp = int(val * (track_height / 2 - 10))
                x = i
                
                # Determine color based on whether this time is in an audible segment
                time_at_x = draw_start + ((i / width) * visible_duration)
                in_segment = any(seg['start'] <= time_at_x <= seg['end'] 
                               for seg in self.segments 
                               if seg.get('type') == 'audible')
                color = active_color if in_segment else dim_color
                
                # Draw a vertical line representing this audio sample
                self.waveform_canvas.create_line(x, track_center_y - amp, x, track_center_y + amp,
                                                fill=color, width=1)
    
    def draw_segments(self, width, height, visible_duration, draw_start=0.0, draw_end=None):
        """
        Draw segment visualization showing what will be kept vs removed, supporting zoom.
        
        Args:
            width: Width of the segments canvas
            height: Height of the segments canvas
            visible_duration: Duration of the visible area in seconds
            draw_start: Start time to draw from (default: 0.0)
            draw_end: End time to draw to (default: duration)
        """
        if draw_end is None:
            draw_end = self.duration
        
        # Background (silence) - dark color for parts that will be removed
        self.segments_canvas.create_rectangle(0, 0, width, height, fill=AppColors.SEGMENT_REMOVE, outline="")
        
        # Draw all segments (both audible and silent)
        for seg in self.segments:
            start = seg['start']
            end = seg['end']
            seg_type = seg.get('type', 'audible')
            keep = seg.get('keep', True)
            
            # Only draw segments that are visible in the current draw area
            if end < draw_start or start > draw_end:
                continue
            
            # Calculate pixel positions for this segment (relative to draw area)
            x1 = ((start - draw_start) / visible_duration) * width
            x2 = ((end - draw_start) / visible_duration) * width
            
            # Clamp to canvas bounds
            x1 = max(0, x1)
            x2 = min(width, x2)
            
            # Choose color based on segment type, keep status, and AI decision
            if seg_type == 'audible':
                if keep:
                    # Audible segments that will be kept - green
                    fill_color = AppColors.SEGMENT_KEEP
                    border_color = AppColors.SEGMENT_BORDER
                else:
                    # Audible segments marked for removal - check AI decision
                    ai_decision = seg.get('ai_decision')
                    if ai_decision == 'FLAG':
                        # AI flagged for removal - purple
                        fill_color = AppColors.SEGMENT_AI_FLAG
                        border_color = AppColors.SEGMENT_AI_FLAG
                    elif ai_decision == 'UNCERTAIN':
                        # Uncertain - default to flagged - orange
                        fill_color = AppColors.SEGMENT_UNCERTAIN
                        border_color = AppColors.SEGMENT_UNCERTAIN
                    else:
                        # Manual removal - orange
                        fill_color = AppColors.SEGMENT_MANUAL_REMOVE
                        border_color = AppColors.SEGMENT_MANUAL_REMOVE
            elif seg_type == 'silent':
                if keep:
                    # Silent segments that are kept - gray
                    fill_color = AppColors.SEGMENT_SILENT_KEEP
                    border_color = AppColors.SEGMENT_SILENT_KEEP
                else:
                    # Silent segments that will be removed - red
                    fill_color = AppColors.SEGMENT_REMOVE
                    border_color = AppColors.SEGMENT_REMOVE
            else:
                # Fallback (shouldn't happen)
                fill_color = "#808080"
                border_color = "#606060"
            
            # Draw rectangle for the segment
            self.segments_canvas.create_rectangle(x1, 0, x2, height,
                                                 fill=fill_color, outline="")
            # Draw borders to make segments more visible
            self.segments_canvas.create_line(x1, 0, x1, height, fill=border_color, width=2)
            self.segments_canvas.create_line(x2, 0, x2, height, fill=border_color, width=2)
    
    def draw_playhead(self, wave_width, wave_height, seg_width, seg_height, visible_duration, draw_start=0.0, draw_end=None):
        """
        Draw red playhead at current position across all sections, supporting zoom.
        
        Args:
            wave_width: Width of the waveform canvas
            wave_height: Height of the waveform canvas
            seg_width: Width of the segments canvas
            seg_height: Height of the segments canvas
            visible_duration: Duration of the visible area in seconds
            draw_start: Start time to draw from (default: 0.0)
            draw_end: End time to draw to (default: duration)
        """
        if draw_end is None:
            draw_end = self.duration
        
        if self.duration == 0:
            return
        
        # Only draw playhead if it's within the draw area
        if self.playhead_time < draw_start or self.playhead_time > draw_end:
            return
        
        # Calculate x position for the playhead (relative to draw area)
        wave_x = ((self.playhead_time - draw_start) / visible_duration) * wave_width
        seg_x = ((self.playhead_time - draw_start) / visible_duration) * seg_width
        
        # Draw playhead on waveform canvas
        self.waveform_canvas.create_line(wave_x, 0, wave_x, wave_height,
                                        fill="#ff4444", width=3, tags="playhead")
        
        # Draw playhead on segments canvas
        self.segments_canvas.create_line(seg_x, 0, seg_x, seg_height,
                                        fill="#ff4444", width=3, tags="playhead")
    
    def on_canvas_click(self, event):
        """
        Handle click on timeline.
        Starts dragging mode and updates playhead position.
        
        Args:
            event: Mouse click event
        """
        self.dragging = True
        self.update_playhead_from_click(event.x, event.widget.winfo_width())
    
    def on_segment_click(self, event):
        """
        Handle click on segment canvas to toggle segments (both audible and silent).
        
        This method allows users to click on any segment to toggle whether
        it should be kept or removed:
        - Green segments (audible): Click to mark as remove (keep=False)
        - Red segments (bad silence): Click to mark as keep (keep=True, gray)
        - Gray segments (good silence): Click to mark as remove (keep=False, red)
        
        Args:
            event: Mouse click event containing x coordinate
        """
        if self.duration == 0 or not self.segments:
            return
        
        # Get canvas width
        width = self.segments_canvas.winfo_width() or 800
        
        # Calculate draw area based on zoom level
        if self.zoom_level <= 1.0:
            # When zoomed out, use full timeline
            draw_start = 0.0
            draw_end = self.duration
            visible_duration = self.duration
        else:
            # When zoomed in, use visible area
            draw_start = self.view_start
            draw_end = self.view_end
            visible_duration = self.view_end - self.view_start
        
        # Calculate the time that was clicked (relative to draw area)
        click_ratio = event.x / width
        time_clicked = draw_start + (click_ratio * visible_duration)
        
        # Find which segment was clicked
        for seg in self.segments:
            if seg['start'] <= time_clicked <= seg['end']:
                # Toggle the keep status for any segment type
                current_keep = seg.get('keep', True)
                seg['keep'] = not current_keep
                
                # Redraw the timeline to show the change
                self.draw_timeline()
                
                # Update statistics
                self.update_statistics()
                
                # Print feedback for debugging
                seg_type = seg.get('type', 'unknown')
                status = "kept" if seg['keep'] else "removed"
                print(f"{seg_type.capitalize()} segment at {seg['start']:.1f}s-{seg['end']:.1f}s will be {status}")
                break
    
    def on_canvas_drag(self, event):
        """
        Handle dragging on timeline.
        Updates playhead position while dragging.
        
        Args:
            event: Mouse drag event
        """
        if self.dragging:
            self.update_playhead_from_click(event.x, event.widget.winfo_width())
    
    def on_canvas_release(self, event):
        """
        Handle mouse release.
        Stops dragging mode.
        
        Args:
            event: Mouse release event
        """
        self.dragging = False
    
    def update_playhead_from_click(self, x, width):
        """
        Update playhead position from click coordinates, supporting zoom.
        
        Args:
            x: X coordinate of the click
            width: Width of the canvas that was clicked
        """
        if self.duration == 0 or width == 0:
            return
        
        # Calculate draw area based on zoom level
        if self.zoom_level <= 1.0:
            # When zoomed out, use full timeline
            draw_start = 0.0
            draw_end = self.duration
            visible_duration = self.duration
        else:
            # When zoomed in, use visible area
            draw_start = self.view_start
            draw_end = self.view_end
            visible_duration = self.view_end - self.view_start
        
        # Convert click position to time (relative to draw area)
        click_ratio = x / width
        clicked_time = draw_start + (click_ratio * visible_duration)
        
        # Clamp to valid range
        self.playhead_time = max(0, min(clicked_time, self.duration))
        
        # Get current canvas dimensions
        wave_width = self.waveform_canvas.winfo_width() or 800
        wave_height = self.waveform_canvas.winfo_height() or 80
        seg_width = self.segments_canvas.winfo_width() or 800
        seg_height = self.segments_canvas.winfo_height() or 80  # Match waveform height
        
        # Remove old playheads
        self.waveform_canvas.delete("playhead")
        self.segments_canvas.delete("playhead")
        
        # Draw new playhead with zoom support (use same draw area as click calculation)
        self.draw_playhead(wave_width, wave_height, seg_width, seg_height, visible_duration, draw_start, draw_end)
        
        # Call the callback function if provided
        if self.on_time_click:
            self.on_time_click(self.playhead_time)
    
    def on_mouse_wheel(self, event):
        """
        Handle mouse wheel events for zooming.
        
        Args:
            event: Mouse wheel event
        """
        if self.duration == 0:
            return
        
        # Determine zoom direction
        if event.delta > 0 or event.num == 4:  # Scroll up or wheel up
            self.zoom_in()
        elif event.delta < 0 or event.num == 5:  # Scroll down or wheel down
            self.zoom_out()
    
    def zoom_in(self):
        """
        Zoom in on the timeline (show less time, more detail).
        """
        if self.duration == 0:
            return
        
        # Increase zoom level
        new_zoom = min(self.zoom_level * 1.5, self.max_zoom)
        
        if new_zoom != self.zoom_level:
            # Calculate center of current view
            center_time = (self.view_start + self.view_end) / 2
            
            # Calculate new view duration
            new_duration = self.duration / new_zoom
            
            # Update view bounds centered on current center
            self.view_start = max(0, center_time - new_duration / 2)
            self.view_end = min(self.duration, center_time + new_duration / 2)
            
            # Adjust if we hit boundaries
            if self.view_start == 0:
                self.view_end = min(self.duration, new_duration)
            elif self.view_end == self.duration:
                self.view_start = max(0, self.duration - new_duration)
            
            self.zoom_level = new_zoom
            self.update_zoom_display()
            self.draw_timeline()
    
    def zoom_out(self):
        """
        Zoom out on the timeline (show more time, less detail).
        Anchors to the right side (end of timeline) so it doesn't leave empty space.
        """
        if self.duration == 0:
            return
        
        # Decrease zoom level
        new_zoom = max(self.zoom_level / 1.5, self.min_zoom)
        
        if new_zoom != self.zoom_level:
            # Calculate new view duration
            new_duration = self.duration / new_zoom
            
            # Anchor to the right side: keep view_end at duration, adjust view_start
            self.view_end = self.duration
            self.view_start = max(0, self.duration - new_duration)
            
            # If we hit the left boundary, adjust view_end instead
            if self.view_start == 0:
                self.view_end = min(self.duration, new_duration)
            
            self.zoom_level = new_zoom
            self.update_zoom_display()
            self.draw_timeline()
    
    def reset_zoom(self):
        """
        Reset zoom to show the entire timeline.
        Anchors to the right side.
        """
        if self.duration == 0:
            return
        
        self.zoom_level = 1.0
        self.view_start = 0.0
        self.view_end = self.duration
        self.update_zoom_display()
        self.draw_timeline()
    
    def update_zoom_display(self):
        """
        Update the zoom level display label.
        """
        zoom_percent = int(self.zoom_level * 100)
        self.zoom_label.configure(text=f"{zoom_percent}%")
    
    def on_horizontal_scroll(self, event):
        """
        Handle horizontal scrolling with Shift + Mouse Wheel.
        
        Args:
            event: Mouse wheel event
        """
        if self.duration == 0:
            return
        
        # Calculate scroll amount (percentage of visible duration)
        visible_duration = self.view_end - self.view_start
        scroll_amount = visible_duration * 0.1  # 10% of visible area
        
        # Determine scroll direction
        if event.delta > 0 or event.num == 4:  # Scroll up or wheel up
            self.scroll_left(scroll_amount)
        elif event.delta < 0 or event.num == 5:  # Scroll down or wheel down
            self.scroll_right(scroll_amount)
    
    def on_key_press(self, event):
        """
        Handle keyboard arrow key presses for scrolling.
        
        Args:
            event: Key press event
        """
        if self.duration == 0:
            return
        
        visible_duration = self.view_end - self.view_start
        scroll_amount = visible_duration * 0.1  # 10% of visible area
        
        if event.keysym == "Left":
            self.scroll_left(scroll_amount)
        elif event.keysym == "Right":
            self.scroll_right(scroll_amount)
        elif event.keysym == "Home":
            self.scroll_to_start()
        elif event.keysym == "End":
            self.scroll_to_end()
    
    def scroll_left(self, amount=None):
        """
        Scroll the timeline view to the left (earlier in time).
        
        Args:
            amount: Amount to scroll in seconds (if None, uses default)
        """
        if self.duration == 0:
            return
        
        if amount is None:
            visible_duration = self.view_end - self.view_start
            amount = visible_duration * 0.1  # 10% of visible area
        
        # Move view window to the left
        new_start = max(0, self.view_start - amount)
        new_end = new_start + (self.view_end - self.view_start)
        
        # Adjust if we hit the beginning
        if new_start == 0:
            new_end = min(self.duration, self.view_end - self.view_start)
        
        self.view_start = new_start
        self.view_end = new_end
        self.draw_timeline()
    
    def scroll_right(self, amount=None):
        """
        Scroll the timeline view to the right (later in time).
        
        Args:
            amount: Amount to scroll in seconds (if None, uses default)
        """
        if self.duration == 0:
            return
        
        if amount is None:
            visible_duration = self.view_end - self.view_start
            amount = visible_duration * 0.1  # 10% of visible area
        
        # Move view window to the right
        new_end = min(self.duration, self.view_end + amount)
        new_start = new_end - (self.view_end - self.view_start)
        
        # Adjust if we hit the end
        if new_end == self.duration:
            new_start = max(0, self.duration - (self.view_end - self.view_start))
        
        self.view_start = new_start
        self.view_end = new_end
        self.draw_timeline()
    
    def scroll_to_start(self):
        """
        Scroll to the beginning of the timeline.
        """
        if self.duration == 0:
            return
        
        visible_duration = self.view_end - self.view_start
        self.view_start = 0.0
        self.view_end = min(self.duration, visible_duration)
        self.draw_timeline()
    
    def scroll_to_end(self):
        """
        Scroll to the end of the timeline.
        """
        if self.duration == 0:
            return
        
        visible_duration = self.view_end - self.view_start
        self.view_end = self.duration
        self.view_start = max(0, self.duration - visible_duration)
        self.draw_timeline()