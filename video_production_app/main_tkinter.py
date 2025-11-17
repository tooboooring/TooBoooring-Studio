#!/usr/bin/env python3
"""
Direct launcher for Tkinter UI (CustomTkinter-based).

Run: python -m video_production_app.main_tkinter

The Tkinter UI provides a classic desktop interface with advanced features like:
- VLC video player integration
- Keyboard shortcuts
- Mouse wheel zoom
- Batch processing
"""

import sys
from pathlib import Path

# Set up path before relative imports
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from video_production_app.utils.entry_helpers import setup_project_path, handle_launch_error


def launch():
    """Launch the Tkinter UI."""
    print("🖥️  Launching Tkinter UI...")
    print("=" * 50)
    
    # Set up project path
    setup_project_path()
    
    try:
        from video_production_app.ui.app import VideoProductionApp
        
        app = VideoProductionApp()
        app.mainloop()
    except ImportError as e:
        handle_launch_error(e, "Tkinter", "CustomTkinter", "pip install customtkinter")
    except Exception as e:
        handle_launch_error(e, "Tkinter", "CustomTkinter", "pip install customtkinter")


def main():
    """Main entry point."""
    launch()


if __name__ == "__main__":
    main()

