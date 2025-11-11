"""
Batch processing tab for Video Production App.

This module contains the batch processing tab functionality that allows users to
queue multiple videos for processing, monitor progress, and manage the batch queue.
It provides a comprehensive interface for processing multiple videos efficiently.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import List, Optional, Callable

from ..core.settings_manager import SettingsManager
from ..utils.colors import AppColors
from ..utils.helpers import load_icon, add_tooltip


class BatchTab:
    """
    Batch processing tab for the Video Production App.
    
    This class manages the batch processing functionality including:
    - Adding videos to the batch queue
    - Managing queue items (remove, reorder)
    - Monitoring batch processing progress
    - Starting and stopping batch processing
    - Queue status management
    
    Attributes:
        parent: Parent widget (main tab)
        settings: Settings manager instance
        batch_queue: List of videos in the processing queue
        processing: Whether batch processing is currently active
        
    Example usage:
        batch_tab = BatchTab(parent_widget, settings_manager)
        batch_tab.setup_ui()
    """
    
    def __init__(self, parent, settings: SettingsManager):
        """
        Initialize the batch processing tab.
        
        Args:
            parent: Parent widget for the tab
            settings: Settings manager instance
        """
        self.parent = parent
        self.settings = settings
        
        # State variables
        self.batch_queue = []
        self.processing = False
        
        # Widget references
        self.queue_frame = None
        self.add_files_btn = None
        self.start_batch_btn = None
        self.clear_queue_btn = None
        self.status_label = None
        self.progress_bar = None
        
        # Set up the UI
        self.setup_ui()
    
    def setup_ui(self):
        """
        Set up the batch processing tab user interface.
        
        This method creates all the UI elements for the batch processing tab
        including the queue management, controls, and progress monitoring.
        """
        # Configure grid layout
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(1, weight=1)
        
        # Header with controls
        self._create_header()
        
        # Queue display area
        self._create_queue_area()
        
        # Progress and status area
        self._create_progress_area()
    
    def _create_header(self):
        """
        Create the header section with batch controls.
        """
        # Header frame (toolbar)
        header_frame = ctk.CTkFrame(
            self.parent,
            fg_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=4,
            height=50
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="Batch Processing Queue",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        )
        title_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # Control buttons frame
        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        
        # Add files button (icon)
        folder_icon = load_icon("folder", 20)
        self.add_files_btn = ctk.CTkButton(
            btn_frame,
            text="" if folder_icon else "📁",
            image=folder_icon,
            width=32,
            height=32,
            command=self.add_files_to_queue,
            fg_color=AppColors.BG_LIGHT,
            hover_color=AppColors.PRIMARY,
            corner_radius=4
        )
        self.add_files_btn.grid(row=0, column=0, padx=3)
        add_tooltip(self.add_files_btn, "Add Files to Queue")
        
        # Start batch button (icon)
        play_icon = load_icon("play", 20)
        self.start_batch_btn = ctk.CTkButton(
            btn_frame,
            text="" if play_icon else "▶",
            image=play_icon,
            width=32,
            height=32,
            command=self.start_batch_processing,
            fg_color=AppColors.BG_LIGHT,
            hover_color=AppColors.SUCCESS,
            corner_radius=4,
            state="disabled"
        )
        self.start_batch_btn.grid(row=0, column=1, padx=3)
        add_tooltip(self.start_batch_btn, "Start Batch Processing")
        
        # Clear queue button (icon)
        delete_icon = load_icon("delete", 20)
        self.clear_queue_btn = ctk.CTkButton(
            btn_frame,
            text="" if delete_icon else "🗑",
            image=delete_icon,
            width=32,
            height=32,
            command=self.clear_queue,
            fg_color=AppColors.BG_LIGHT,
            hover_color=AppColors.DANGER,
            corner_radius=4,
            state="disabled"
        )
        self.clear_queue_btn.grid(row=0, column=2, padx=3)
        add_tooltip(self.clear_queue_btn, "Clear Queue")
    
    def _create_queue_area(self):
        """
        Create the queue display area.
        """
        # Queue frame panel
        queue_container = ctk.CTkFrame(
            self.parent,
            fg_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=4
        )
        queue_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        queue_container.grid_columnconfigure(0, weight=1)
        queue_container.grid_rowconfigure(0, weight=1)
        
        # Scrollable frame for queue items
        self.queue_frame = ctk.CTkScrollableFrame(
            queue_container,
            fg_color="transparent"
        )
        self.queue_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.queue_frame.grid_columnconfigure(0, weight=1)
        
        # Initial placeholder
        placeholder = ctk.CTkLabel(
            self.queue_frame,
            text="No files in queue\n\nClick 'Add Files' to add videos for batch processing",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_MUTED,
            justify="center"
        )
        placeholder.grid(row=0, column=0, pady=50)
    
    def _create_progress_area(self):
        """
        Create the progress and status area.
        """
        # Progress frame panel
        progress_frame = ctk.CTkFrame(
            self.parent,
            fg_color=AppColors.BG_MEDIUM,
            border_width=1,
            border_color=AppColors.BORDER,
            corner_radius=4
        )
        progress_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Section title
        title_label = ctk.CTkLabel(
            progress_frame,
            text="Batch Progress",
            font=("Segoe UI", 12, "bold"),
            text_color=AppColors.TEXT_PRIMARY
        )
        title_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=20,
            progress_color=AppColors.SUCCESS,
            fg_color=AppColors.BG_LIGHT
        )
        self.progress_bar.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="ew")
        self.progress_bar.set(0)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            progress_frame,
            text="Ready to process batch",
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_SECONDARY
        )
        self.status_label.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")
    
    def add_files_to_queue(self):
        """
        Add multiple video files to the batch queue.
        """
        # Open file dialog for multiple files
        file_paths = filedialog.askopenfilenames(
            title="Select Video Files for Batch Processing",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v"),
                ("All files", "*.*")
            ]
        )
        
        if not file_paths:
            return
        
        # Add files to queue
        added_count = 0
        for file_path in file_paths:
            if file_path not in [item["path"] for item in self.batch_queue]:
                self.batch_queue.append({
                    "path": file_path,
                    "name": Path(file_path).name,
                    "status": "pending"
                })
                added_count += 1
        
        # Update UI
        self._update_queue_display()
        self._update_button_states()
        
        # Show status
        self.status_label.configure(text=f"Added {added_count} file(s) to queue")
    
    def clear_queue(self):
        """
        Clear all items from the batch queue.
        """
        if self.batch_queue:
            # Confirm with user
            result = messagebox.askyesno(
                "Clear Queue",
                f"Are you sure you want to remove all {len(self.batch_queue)} files from the queue?"
            )
            
            if result:
                self.batch_queue.clear()
                self._update_queue_display()
                self._update_button_states()
                self.status_label.configure(text="Queue cleared")
    
    def remove_from_queue(self, file_path: str):
        """
        Remove a specific file from the batch queue.
        
        Args:
            file_path: Path of the file to remove
        """
        self.batch_queue = [item for item in self.batch_queue if item["path"] != file_path]
        self._update_queue_display()
        self._update_button_states()
    
    def start_batch_processing(self):
        """
        Start processing the batch queue.
        """
        if not self.batch_queue or self.processing:
            return
        
        # Confirm with user
        result = messagebox.askyesno(
            "Start Batch Processing",
            f"Start processing {len(self.batch_queue)} files? This may take a while."
        )
        
        if not result:
            return
        
        # Start processing
        self.processing = True
        self.start_batch_btn.configure(state="disabled", text="Processing...")
        self.add_files_btn.configure(state="disabled")
        self.clear_queue_btn.configure(state="disabled")
        
        # Update status
        self.status_label.configure(text="Starting batch processing...")
        
        # In a real implementation, this would start the actual processing
        # For now, we'll simulate it
        self._simulate_batch_processing()
    
    def _simulate_batch_processing(self):
        """
        Simulate batch processing for demonstration.
        """
        import threading
        import time
        
        def process_batch():
            total_files = len(self.batch_queue)
            
            for i, item in enumerate(self.batch_queue):
                # Update item status
                item["status"] = "processing"
                self._update_queue_display()
                
                # Update progress
                progress = (i / total_files) * 100
                self.progress_bar.set(progress / 100)
                self.status_label.configure(text=f"Processing {item['name']} ({i+1}/{total_files})")
                
                # Simulate processing time
                time.sleep(2)
                
                # Mark as completed
                item["status"] = "completed"
                self._update_queue_display()
            
            # Processing complete
            self.progress_bar.set(1.0)
            self.status_label.configure(text=f"Batch processing completed! Processed {total_files} files.")
            
            # Reset UI
            self.processing = False
            self.start_batch_btn.configure(state="normal", text="▶ Start Batch")
            self.add_files_btn.configure(state="normal")
            self.clear_queue_btn.configure(state="normal")
        
        # Start processing in background thread
        processing_thread = threading.Thread(target=process_batch)
        processing_thread.daemon = True
        processing_thread.start()
    
    def _update_queue_display(self):
        """
        Update the queue display with current items.
        """
        # Clear existing items
        for widget in self.queue_frame.winfo_children():
            widget.destroy()
        
        if not self.batch_queue:
            # Show placeholder
            placeholder = ctk.CTkLabel(
                self.queue_frame,
                text="No files in queue\n\nClick 'Add Files' to add videos for batch processing",
                font=("Segoe UI", 14),
                text_color=AppColors.TEXT_MUTED,
                justify="center"
            )
            placeholder.grid(row=0, column=0, pady=50)
            return
        
        # Display queue items
        for i, item in enumerate(self.batch_queue):
            self._create_queue_item(i, item)
    
    def _create_queue_item(self, index: int, item: dict):
        """
        Create a queue item widget.
        
        Args:
            index: Index of the item in the queue
            item: Dictionary containing item information
        """
        # Item frame
        item_frame = ctk.CTkFrame(
            self.queue_frame,
            fg_color=AppColors.BG_LIGHT,
            corner_radius=8,
            border_width=1,
            border_color=AppColors.BORDER
        )
        item_frame.grid(row=index, column=0, sticky="ew", pady=5)
        item_frame.grid_columnconfigure(1, weight=1)
        
        # Status indicator
        status_colors = {
            "pending": AppColors.TEXT_SECONDARY,
            "processing": AppColors.PRIMARY,
            "completed": AppColors.SUCCESS,
            "failed": AppColors.DANGER
        }
        
        status_icons = {
            "pending": "⏸",
            "processing": "▶️",
            "completed": "✅",
            "failed": "❌"
        }
        
        status_label = ctk.CTkLabel(
            item_frame,
            text=status_icons.get(item["status"], "⏸"),
            font=("Segoe UI", 16),
            text_color=status_colors.get(item["status"], AppColors.TEXT_SECONDARY),
            width=30
        )
        status_label.grid(row=0, column=0, padx=10, pady=10)
        
        # File name
        name_label = ctk.CTkLabel(
            item_frame,
            text=item["name"],
            font=("Segoe UI", 12),
            text_color=AppColors.TEXT_PRIMARY,
            anchor="w"
        )
        name_label.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Remove button
        if item["status"] == "pending":
            remove_btn = ctk.CTkButton(
                item_frame,
                text="✕",
                command=lambda: self.remove_from_queue(item["path"]),
                width=30,
                height=30,
                fg_color="transparent",
                hover_color=AppColors.DANGER
            )
            remove_btn.grid(row=0, column=2, padx=10, pady=10)
    
    def _update_button_states(self):
        """
        Update button states based on queue status.
        """
        has_items = len(self.batch_queue) > 0
        
        if has_items and not self.processing:
            self.start_batch_btn.configure(state="normal")
            self.clear_queue_btn.configure(state="normal")
        else:
            self.start_batch_btn.configure(state="disabled")
            self.clear_queue_btn.configure(state="disabled")
    
    def get_queue_status(self):
        """
        Get the current status of the batch queue.
        
        Returns:
            Dictionary with queue statistics
        """
        total = len(self.batch_queue)
        pending = len([item for item in self.batch_queue if item["status"] == "pending"])
        processing = len([item for item in self.batch_queue if item["status"] == "processing"])
        completed = len([item for item in self.batch_queue if item["status"] == "completed"])
        failed = len([item for item in self.batch_queue if item["status"] == "failed"])
        
        return {
            "total": total,
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "is_processing": self.processing
        }
