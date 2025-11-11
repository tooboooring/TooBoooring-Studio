"""
Advanced settings tab for Video Production App.

This module contains the advanced settings tab functionality that allows users to
configure silence detection parameters, trim controls, and other advanced options.
It provides a comprehensive interface for fine-tuning the video processing behavior.
"""

import customtkinter as ctk
from typing import Optional, Callable

from ..core.settings_manager import SettingsManager
from ..utils.colors import AppColors
from ..utils.helpers import load_icon, add_tooltip


class AdvancedTab:
    """
    Advanced settings tab for the Video Production App.
    
    This class manages the advanced settings functionality including:
    - Silence detection parameters (threshold, duration, padding)
    - Trim controls (start/end times)
    - Output quality settings
    - Advanced processing options
    - Settings persistence and reset
    
    Attributes:
        parent: Parent widget (main tab)
        settings: Settings manager instance
        on_settings_change: Optional callback for settings changes
        
    Example usage:
        advanced_tab = AdvancedTab(parent_widget, settings_manager)
        advanced_tab.setup_ui()
    """
    
    def __init__(self, parent, settings: SettingsManager, 
                 on_settings_change: Optional[Callable] = None):
        """
        Initialize the advanced settings tab.
        
        Args:
            parent: Parent widget for the tab
            settings: Settings manager instance
            on_settings_change: Optional callback function for settings changes
        """
        self.parent = parent
        self.settings = settings
        self.on_settings_change = on_settings_change
        
        # Widget references
        self.silence_db_var = None
        self.silence_duration_var = None
        self.pad_before_var = None
        self.pad_after_var = None
        self.trim_start_var = None
        self.trim_end_var = None
        
        # Set up the UI
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        """
        Set up the advanced settings tab user interface.
        
        This method creates all the UI elements for the advanced settings tab
        including parameter controls, trim settings, and action buttons.
        """
        # Configure grid layout
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(0, weight=1)
        
        # Create scrollable frame for content
        scrollable_frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # Silence detection section
        self._create_silence_section(scrollable_frame)
        
        # Trim controls section
        self._create_trim_section(scrollable_frame)
        
        # Advanced options section
        self._create_advanced_section(scrollable_frame)
        
        # Action buttons section
        self._create_actions_section(scrollable_frame)
    
    def _create_silence_section(self, parent):
        """
        Create the silence detection parameters section.
        
        Args:
            parent: Parent widget for the section
        """
        # Silence detection frame panel
        silence_frame = ctk.CTkFrame(
            parent,
            fg_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=4
        )
        silence_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        silence_frame.grid_columnconfigure(1, weight=1)
        
        # Section title
        title_label = ctk.CTkLabel(
            silence_frame,
            text="Silence Detection Parameters",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        )
        title_label.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 10), sticky="w")
        
        # Silence threshold (dB)
        ctk.CTkLabel(
            silence_frame,
            text="Silence Threshold (dB):",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        
        self.silence_db_var = ctk.DoubleVar(value=-40)
        silence_db_slider = ctk.CTkSlider(
            silence_frame,
            from_=-60,
            to=-20,
            number_of_steps=40,
            variable=self.silence_db_var,
            command=self._on_silence_db_change
        )
        silence_db_slider.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="ew")
        
        self.silence_db_label = ctk.CTkLabel(
            silence_frame,
            text="-40 dB",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_SECONDARY
        )
        self.silence_db_label.grid(row=1, column=2, padx=(0, 10), pady=(0, 10), sticky="w")
        
        # Silence duration (seconds)
        ctk.CTkLabel(
            silence_frame,
            text="Minimum Silence Duration (s):",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")
        
        self.silence_duration_var = ctk.DoubleVar(value=0.7)
        silence_duration_slider = ctk.CTkSlider(
            silence_frame,
            from_=0.1,
            to=3.0,
            number_of_steps=29,
            variable=self.silence_duration_var,
            command=self._on_silence_duration_change
        )
        silence_duration_slider.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="ew")
        
        self.silence_duration_label = ctk.CTkLabel(
            silence_frame,
            text="0.7 s",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_SECONDARY
        )
        self.silence_duration_label.grid(row=2, column=2, padx=(0, 10), pady=(0, 10), sticky="w")
        
        # Padding before silence (seconds)
        ctk.CTkLabel(
            silence_frame,
            text="Padding Before Silence (s):",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=3, column=0, padx=10, pady=(0, 10), sticky="w")
        
        self.pad_before_var = ctk.DoubleVar(value=0.1)
        pad_before_slider = ctk.CTkSlider(
            silence_frame,
            from_=0.0,
            to=1.0,
            number_of_steps=20,
            variable=self.pad_before_var,
            command=self._on_pad_before_change
        )
        pad_before_slider.grid(row=3, column=1, padx=10, pady=(0, 10), sticky="ew")
        
        self.pad_before_label = ctk.CTkLabel(
            silence_frame,
            text="0.1 s",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_SECONDARY
        )
        self.pad_before_label.grid(row=3, column=2, padx=(0, 10), pady=(0, 10), sticky="w")
        
        # Padding after silence (seconds)
        ctk.CTkLabel(
            silence_frame,
            text="Padding After Silence (s):",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=4, column=0, padx=10, pady=(0, 10), sticky="w")
        
        self.pad_after_var = ctk.DoubleVar(value=0.0)
        pad_after_slider = ctk.CTkSlider(
            silence_frame,
            from_=0.0,
            to=1.0,
            number_of_steps=20,
            variable=self.pad_after_var,
            command=self._on_pad_after_change
        )
        pad_after_slider.grid(row=4, column=1, padx=10, pady=(0, 10), sticky="ew")
        
        self.pad_after_label = ctk.CTkLabel(
            silence_frame,
            text="0.0 s",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_SECONDARY
        )
        self.pad_after_label.grid(row=4, column=2, padx=(0, 10), pady=(0, 10), sticky="w")
    
    def _create_trim_section(self, parent):
        """
        Create the trim controls section.
        
        Args:
            parent: Parent widget for the section
        """
        # Trim controls frame panel
        trim_frame = ctk.CTkFrame(
            parent,
            fg_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=4
        )
        trim_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        trim_frame.grid_columnconfigure(1, weight=1)
        
        # Section title
        title_label = ctk.CTkLabel(
            trim_frame,
            text="Trim Controls",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        )
        title_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 10), sticky="w")
        
        # Trim start time
        ctk.CTkLabel(
            trim_frame,
            text="Start Time (seconds):",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        
        self.trim_start_var = ctk.StringVar(value="0")
        trim_start_entry = ctk.CTkEntry(
            trim_frame,
            textvariable=self.trim_start_var,
            width=150,
            height=28,
            placeholder_text="0.0"
        )
        trim_start_entry.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="w")
        
        # Trim end time
        ctk.CTkLabel(
            trim_frame,
            text="End Time (seconds):",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")
        
        self.trim_end_var = ctk.StringVar(value="")
        trim_end_entry = ctk.CTkEntry(
            trim_frame,
            textvariable=self.trim_end_var,
            width=150,
            height=28,
            placeholder_text="Leave empty for full duration"
        )
        trim_end_entry.grid(row=2, column=1, padx=10, pady=(0, 10), sticky="w")
        
        # Help text
        help_text = ctk.CTkLabel(
            trim_frame,
            text="Tip: Leave end time empty to process the entire video",
            font=("Segoe UI", 10),
            text_color=AppColors.TEXT_MUTED
        )
        help_text.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")
    
    def _create_advanced_section(self, parent):
        """
        Create the advanced options section.
        
        Args:
            parent: Parent widget for the section
        """
        # Advanced options frame panel
        advanced_frame = ctk.CTkFrame(
            parent,
            fg_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=4
        )
        advanced_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        # Section title
        title_label = ctk.CTkLabel(
            advanced_frame,
            text="Advanced Options",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        )
        title_label.grid(row=0, column=0, padx=10, pady=(10, 10), sticky="w")
        
        # Filter length threshold
        ctk.CTkLabel(
            advanced_frame,
            text="Filter Length Threshold:",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_PRIMARY
        ).grid(row=1, column=0, padx=10, pady=(0, 10), sticky="w")
        
        self.filter_threshold_var = ctk.IntVar(value=4096)
        filter_threshold_entry = ctk.CTkEntry(
            advanced_frame,
            textvariable=self.filter_threshold_var,
            width=150,
            height=28
        )
        filter_threshold_entry.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="w")
        
        # Help text for filter threshold
        help_text = ctk.CTkLabel(
            advanced_frame,
            text="Higher values handle longer videos better but use more memory",
            font=("Segoe UI", 10),
            text_color=AppColors.TEXT_MUTED
        )
        help_text.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")
    
    def _create_actions_section(self, parent):
        """
        Create the action buttons section.
        
        Args:
            parent: Parent widget for the section
        """
        # Actions frame panel
        actions_frame = ctk.CTkFrame(
            parent,
            fg_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=4
        )
        actions_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        
        # Section title
        title_label = ctk.CTkLabel(
            actions_frame,
            text="Actions",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        )
        title_label.grid(row=0, column=0, padx=10, pady=(10, 10), sticky="w")
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        buttons_frame.grid(row=1, column=0, pady=(0, 10))
        
        # Save settings button (icon)
        save_icon = load_icon("save", 20)
        save_btn = ctk.CTkButton(
            buttons_frame,
            text="" if save_icon else "💾",
            image=save_icon,
            width=32,
            height=32,
            command=self.save_settings,
            fg_color=AppColors.BG_LIGHT,
            hover_color=AppColors.SUCCESS,
            corner_radius=4
        )
        save_btn.grid(row=0, column=0, padx=5)
        add_tooltip(save_btn, "Save Settings")
        
        # Reset to defaults button (icon)
        reset_icon = load_icon("reset", 20)
        reset_btn = ctk.CTkButton(
            buttons_frame,
            text="" if reset_icon else "🔄",
            image=reset_icon,
            width=32,
            height=32,
            command=self.reset_to_defaults,
            fg_color=AppColors.BG_LIGHT,
            hover_color=AppColors.WARNING,
            corner_radius=4
        )
        reset_btn.grid(row=0, column=1, padx=5)
        add_tooltip(reset_btn, "Reset to Defaults")
        
        # Load settings button (icon)
        folder_icon = load_icon("folder", 20)
        load_btn = ctk.CTkButton(
            buttons_frame,
            text="" if folder_icon else "📂",
            image=folder_icon,
            width=32,
            height=32,
            command=self.load_settings,
            fg_color=AppColors.BG_LIGHT,
            hover_color=AppColors.INFO,
            corner_radius=4
        )
        load_btn.grid(row=0, column=2, padx=5)
        add_tooltip(load_btn, "Load Settings")
    
    def _on_silence_db_change(self, value):
        """
        Handle silence threshold slider change.
        
        Args:
            value: New threshold value
        """
        self.silence_db_label.configure(text=f"{value:.0f} dB")
        self._notify_settings_change()
    
    def _on_silence_duration_change(self, value):
        """
        Handle silence duration slider change.
        
        Args:
            value: New duration value
        """
        self.silence_duration_label.configure(text=f"{value:.1f} s")
        self._notify_settings_change()
    
    def _on_pad_before_change(self, value):
        """
        Handle padding before slider change.
        
        Args:
            value: New padding value
        """
        self.pad_before_label.configure(text=f"{value:.1f} s")
        self._notify_settings_change()
    
    def _on_pad_after_change(self, value):
        """
        Handle padding after slider change.
        
        Args:
            value: New padding value
        """
        self.pad_after_label.configure(text=f"{value:.1f} s")
        self._notify_settings_change()
    
    def _notify_settings_change(self):
        """
        Notify parent of settings changes.
        """
        if self.on_settings_change:
            self.on_settings_change()
    
    def save_settings(self):
        """
        Save current settings to the settings manager.
        """
        try:
            # Get current values
            self.settings.set("silence_db", self.silence_db_var.get())
            self.settings.set("silence_duration", self.silence_duration_var.get())
            self.settings.set("pad_before", self.pad_before_var.get())
            self.settings.set("pad_after", self.pad_after_var.get())
            self.settings.set("filter_length_threshold", self.filter_threshold_var.get())
            
            # Show success message
            ctk.CTkLabel(
                self.parent,
                text="✅ Settings saved successfully!",
                font=("Segoe UI", 12),
                text_color=AppColors.SUCCESS
            ).grid(row=4, column=0, pady=10)
            
        except Exception as e:
            # Show error message
            ctk.CTkLabel(
                self.parent,
                text=f"❌ Error saving settings: {e}",
                font=("Segoe UI", 12),
                text_color=AppColors.DANGER
            ).grid(row=4, column=0, pady=10)
    
    def load_settings(self):
        """
        Load settings from the settings manager.
        """
        self.load_current_settings()
        
        # Show success message
        ctk.CTkLabel(
            self.parent,
            text="✅ Settings loaded successfully!",
            font=("Segoe UI", 12),
            text_color=AppColors.SUCCESS
        ).grid(row=4, column=0, pady=10)
    
    def reset_to_defaults(self):
        """
        Reset all settings to their default values.
        """
        # Reset to default values
        self.silence_db_var.set(-40)
        self.silence_duration_var.set(0.7)
        self.pad_before_var.set(0.1)
        self.pad_after_var.set(0.0)
        self.filter_threshold_var.set(4096)
        self.trim_start_var.set("0")
        self.trim_end_var.set("")
        
        # Update labels
        self.silence_db_label.configure(text="-40 dB")
        self.silence_duration_label.configure(text="0.7 s")
        self.pad_before_label.configure(text="0.1 s")
        self.pad_after_label.configure(text="0.0 s")
        
        # Show success message
        ctk.CTkLabel(
            self.parent,
            text="✅ Settings reset to defaults!",
            font=("Segoe UI", 12),
            text_color=AppColors.SUCCESS
        ).grid(row=4, column=0, pady=10)
    
    def load_current_settings(self):
        """
        Load current settings from the settings manager.
        """
        # Load settings values
        self.silence_db_var.set(self.settings.get("silence_db", -40))
        self.silence_duration_var.set(self.settings.get("silence_duration", 0.7))
        self.pad_before_var.set(self.settings.get("pad_before", 0.1))
        self.pad_after_var.set(self.settings.get("pad_after", 0.0))
        self.filter_threshold_var.set(self.settings.get("filter_length_threshold", 4096))
        
        # Update labels
        self.silence_db_label.configure(text=f"{self.silence_db_var.get():.0f} dB")
        self.silence_duration_label.configure(text=f"{self.silence_duration_var.get():.1f} s")
        self.pad_before_label.configure(text=f"{self.pad_before_var.get():.1f} s")
        self.pad_after_label.configure(text=f"{self.pad_after_var.get():.1f} s")
    
    def get_trim_settings(self):
        """
        Get the current trim settings.
        
        Returns:
            Tuple of (trim_start, trim_end) where trim_end can be None
        """
        try:
            trim_start = float(self.trim_start_var.get()) if self.trim_start_var.get() else 0.0
            trim_end = float(self.trim_end_var.get()) if self.trim_end_var.get() else None
            return trim_start, trim_end
        except ValueError:
            return 0.0, None
