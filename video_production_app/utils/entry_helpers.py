"""
Shared utilities for entry points.

This module provides common functionality for all entry points including
path setup, error handling, and launch functions.
"""

import sys
import os
from pathlib import Path
from typing import Optional


def setup_project_path() -> Path:
    """
    Set up the project root path and add it to sys.path.
    
    This function automatically detects the project root by looking for
    the video_production_app package directory. It handles both development
    and frozen (PyInstaller) execution modes.
    
    Returns:
        Path to the project root directory
        
    Example:
        project_root = setup_project_path()
        # Now imports will work correctly
    """
    # Handle frozen executables (PyInstaller)
    if getattr(sys, 'frozen', False):
        # If frozen, the executable is in the root directory
        project_root = Path(sys.executable).parent
    else:
        # Find the video_production_app package directory
        current_file = Path(__file__).resolve()
        
        # Walk up the directory tree to find video_production_app package
        for parent in [current_file.parent] + list(current_file.parents):
            if (parent / "video_production_app" / "__init__.py").exists():
                project_root = parent
                break
        else:
            # Fallback: assume we're in video_production_app/utils/
            project_root = current_file.parent.parent
    
    # Add to sys.path if not already there
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root


def handle_launch_error(error: Exception, ui_type: str, package_name: str, install_command: str) -> None:
    """
    Handle errors during UI launch with consistent formatting.
    
    Args:
        error: The exception that occurred
        ui_type: Type of UI ("Tkinter" or "Web")
        package_name: Name of the required package
        install_command: pip install command for the package
        
    Example:
        try:
            launch_ui()
        except ImportError as e:
            handle_launch_error(e, "Web", "PyWebView", "pip install pywebview")
    """
    if isinstance(error, ImportError):
        print(f"❌ Error: Could not import {ui_type} UI dependencies.")
        print(f"   Make sure {package_name} is installed: {install_command}")
        print(f"   Error details: {error}")
    else:
        print(f"❌ Error launching {ui_type} UI: {error}")
        import traceback
        traceback.print_exc()
    
    sys.exit(1)

