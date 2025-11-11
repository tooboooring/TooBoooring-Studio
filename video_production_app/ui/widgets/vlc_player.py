"""
VLC Player Widget for the Video Production App.

This module contains the VLCPlayer class, which integrates a python-vlc
media player into a customtkinter frame for embedded video playback.
"""

import vlc
import os
from datetime import timedelta
import customtkinter as ctk
from typing import List, Dict, Any
from ...utils.helpers import load_icon, add_tooltip

# Optional: If VLC isn't in the system PATH, help the library find it.
# You might need to uncomment and update this path.
# os.environ['PYTHON_VLC_MODULE_PATH'] = r"C:\Program Files\VideoLAN\VLC"


class VLCPlayer(ctk.CTkFrame):
    """
    An embedded VLC video player widget.
    """
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.video_path = None
        self.duration = 0
        self.segments: List[Dict[str, Any]] = []
        self.is_playing = False
        
        # --- VLC Setup ---
        try:
            self.vlc_instance = vlc.Instance("--no-xlib")
            self.media_player = self.vlc_instance.media_player_new()
        except Exception as e:
            print(f"Error initializing VLC: {e}")
            print("Please ensure VLC Media Player is installed.")
            # Show an error label in the UI
            error_label = ctk.CTkLabel(self, text="Error: VLC Media Player not found.\nPlease install it to use the video preview.")
            error_label.grid(row=0, column=0, sticky="nsew")
            self.grid_rowconfigure(0, weight=1)
            self.grid_columnconfigure(0, weight=1)
            return
        
        self.setup_ui()
    
    def setup_ui(self):
        """Create the UI elements for the player."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Video Frame (where VLC will draw)
        self.video_frame = ctk.CTkFrame(self, fg_color="black")
        self.video_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 5))
        
        # 2. Controls Frame - Professional layout
        controls_frame = ctk.CTkFrame(self, fg_color="transparent", height=60)
        controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        controls_frame.grid_propagate(False)
        controls_frame.grid_columnconfigure(2, weight=1)
        
        # Left side: Transport controls
        transport_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        transport_frame.grid(row=0, column=0, sticky="w", padx=5)
        
        # Previous frame button
        self.prev_frame_btn = ctk.CTkButton(
            transport_frame, 
            text="⏮", 
            width=40, 
            height=35,
            command=self.previous_frame,
            font=("Segoe UI", 14)
        )
        self.prev_frame_btn.grid(row=0, column=0, padx=2)
        add_tooltip(self.prev_frame_btn, "Previous Frame")
        
        # Play/Pause Button (larger, more prominent) - using icons
        self.play_icon = load_icon("play", 24)
        self.pause_icon = load_icon("pause", 24)
        self.play_pause_btn = ctk.CTkButton(
            transport_frame, 
            text="" if self.play_icon else "▶", 
            image=self.play_icon,
            width=32, 
            height=32,
            command=self.toggle_play_pause,
            fg_color="#2b2b2b",
            hover_color="#3b3b3b"
        )
        self.play_pause_btn.grid(row=0, column=1, padx=2)
        add_tooltip(self.play_pause_btn, "Play / Pause")
        
        # Next frame button
        self.next_frame_btn = ctk.CTkButton(
            transport_frame, 
            text="⏭", 
            width=40, 
            height=35,
            command=self.next_frame,
            font=("Segoe UI", 14)
        )
        self.next_frame_btn.grid(row=0, column=2, padx=2)
        add_tooltip(self.next_frame_btn, "Next Frame")
        
        # Stop button
        self.stop_btn = ctk.CTkButton(
            transport_frame, 
            text="⏹", 
            width=40, 
            height=35,
            command=self.stop,
            font=("Segoe UI", 14)
        )
        self.stop_btn.grid(row=0, column=3, padx=2)
        add_tooltip(self.stop_btn, "Stop")
        
        # Center: Time display
        time_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        time_frame.grid(row=0, column=1, sticky="", padx=10)
        
        self.time_label = ctk.CTkLabel(
            time_frame, 
            text="00:00:00 / 00:00:00",
            font=("Consolas", 12, "bold")
        )
        self.time_label.grid(row=0, column=0)
        
        # Right side: Options
        options_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        options_frame.grid(row=0, column=2, sticky="e", padx=5)
        
        # "Skip Silence" Checkbox
        self.skip_silence_var = ctk.IntVar(value=0)
        self.skip_silence_check = ctk.CTkCheckBox(
            options_frame, 
            text="Skip Silence", 
            variable=self.skip_silence_var,
            command=self.on_skip_silence_changed
        )
        self.skip_silence_check.grid(row=0, column=0, padx=5)
        
        # Placeholder text
        self.placeholder = ctk.CTkLabel(
            self.video_frame, 
            text="Load a video to begin preview",
            font=("Segoe UI", 14),
            text_color="#888888"
        )
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")
    
    def load_video(self, video_path: str, duration: float, segments: List[Dict[str, Any]]):
        """Load a new video into the player."""
        if not self.vlc_instance:
            return
        
        self.video_path = video_path
        self.duration = duration
        self.segments = segments
        
        try:
            media = self.vlc_instance.media_new(self.video_path)
            self.media_player.set_media(media)
            
            # This is the magic line: tell VLC to draw in our video_frame
            self.media_player.set_hwnd(self.video_frame.winfo_id())
            
            self.placeholder.place_forget()  # Hide placeholder
            self.is_playing = False
            # Set initial play icon
            if self.play_icon:
                self.play_pause_btn.configure(image=self.play_icon, text="")
            else:
                self.play_pause_btn.configure(text="▶")
            self.update_time_label(0)
            
            # Pause immediately to show the first frame (don't auto-play)
            self.media_player.play()
            self.media_player.pause()
            self.is_playing = False
            if self.play_icon:
                self.play_pause_btn.configure(image=self.play_icon, text="")
            else:
                self.play_pause_btn.configure(text="▶")
            
            # Attach event listener for time changes
            self.event_manager = self.media_player.event_manager()
            self.event_manager.event_attach(
                vlc.EventType.MediaPlayerTimeChanged,
                self.on_player_time_changed
            )
            
        except Exception as e:
            print(f"Error loading video in VLC: {e}")
    
    def toggle_play_pause(self):
        """Play or pause the video."""
        if not hasattr(self, 'media_player') or not self.media_player:
            return
            
        if self.is_playing:
            self.media_player.pause()
            # Update button icon
            if self.play_icon:
                self.play_pause_btn.configure(image=self.play_icon, text="")
            else:
                self.play_pause_btn.configure(text="▶")
        else:
            self.media_player.play()
            # Update button icon
            if self.pause_icon:
                self.play_pause_btn.configure(image=self.pause_icon, text="")
            else:
                self.play_pause_btn.configure(text="⏸")
        self.is_playing = not self.is_playing
        # Start time update loop if playing
        if self.is_playing:
            self.update_time_loop()
    
    def stop(self):
        """Stop the video playback."""
        if hasattr(self, 'media_player') and self.media_player:
            self.media_player.stop()
            self.is_playing = False
            # Update button icon
            if self.play_icon:
                self.play_pause_btn.configure(image=self.play_icon, text="")
            else:
                self.play_pause_btn.configure(text="▶")
            self.update_time_label(0)
    
    def previous_frame(self):
        """Go to previous frame."""
        if hasattr(self, 'media_player') and self.media_player:
            current_time = self.media_player.get_time() / 1000.0  # Convert to seconds
            fps = 30  # Default FPS, could be detected from video
            new_time = max(0, current_time - (1.0 / fps))
            self.seek_to_time(new_time)
    
    def next_frame(self):
        """Go to next frame."""
        if hasattr(self, 'media_player') and self.media_player:
            current_time = self.media_player.get_time() / 1000.0  # Convert to seconds
            fps = 30  # Default FPS, could be detected from video
            new_time = min(self.duration, current_time + (1.0 / fps))
            self.seek_to_time(new_time)
    
    def update_time_loop(self):
        """Continuously update time label while playing."""
        if self.is_playing and hasattr(self, 'media_player') and self.media_player:
            current_time = self.media_player.get_time() / 1000.0  # Convert to seconds
            self.update_time_label(current_time)
            # Schedule next update
            self.after(100, self.update_time_loop)  # Update every 100ms
    
    def seek_to_time(self, time_seconds: float):
        """Jump the player to a specific time."""
        self.media_player.set_time(int(time_seconds * 1000))  # VLC uses milliseconds
        # No need to call update_time_label here,
        # the event listener will catch the time change and do it.
    
    def update_time_label(self, current_time_sec: float):
        """Updates the 00:00:00 / 00:00:00 time label."""
        # Format as HH:MM:SS
        duration_td = timedelta(seconds=int(self.duration))
        current_td = timedelta(seconds=int(current_time_sec))
        
        # Format with hours if needed
        duration_str = str(duration_td)
        current_str = str(current_td)
        
        # Ensure format is HH:MM:SS (add leading zero if needed)
        if len(duration_str.split(':')) == 2:
            duration_str = "0:" + duration_str
        if len(current_str.split(':')) == 2:
            current_str = "0:" + current_str
        
        self.time_label.configure(text=f"{current_str} / {duration_str}")
    
    def on_player_time_changed(self, event):
        """
        Callback for VLC's TimeChanged event.
        This runs on a separate thread, so UI calls must be scheduled.
        """
        # Do nothing if checkbox isn't ticked or we have no segments
        if self.skip_silence_var.get() == 0 or not self.segments:
            return
        
        # Don't update if not playing
        if not self.is_playing:
            return
        
        current_time_ms = self.media_player.get_time()
        self.after(0, self.update_time_label, current_time_ms / 1000.0)
        
        # Check if we are inside a "bad silence" (a segment to be cut)
        for segment in self.segments:
            if not segment['keep']:  # Check for *any* segment marked for removal
                start_ms = int(segment['start'] * 1000)
                end_ms = int(segment['end'] * 1000)
                
                # Check if the player is currently inside this segment
                # Add a small buffer (e.g., 50ms) to prevent it from getting stuck
                if (start_ms - 50) <= current_time_ms < end_ms:
                    # This is a thread-safe way to tell the player to seek.
                    # We schedule the 'set_time' call on the main GUI thread.
                    print(f"Skipping segment: jumping to {end_ms}ms")
                    self.after(0, self.media_player.set_time, end_ms)
                    break  # We've jumped, no need to check other segments
    
    def on_skip_silence_changed(self):
        """Handle skip silence checkbox change."""
        # The actual skipping logic is handled in on_player_time_changed
        pass
    
    def cleanup(self):
        """Stop the player on exit."""
        if hasattr(self, 'media_player'):
            self.media_player.stop()
        # Detach event listener if it exists
        if hasattr(self, 'event_manager') and self.event_manager:
            try:
                self.event_manager.event_detach(vlc.EventType.MediaPlayerTimeChanged)
            except Exception:
                pass  # Ignore errors during cleanup

