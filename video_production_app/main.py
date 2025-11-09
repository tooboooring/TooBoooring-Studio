"""
Main entry point for Video Production App v3.

This module serves as the entry point for the refactored Video Production App.
It initializes the application and starts the main event loop.

To run the application:
    python -m video_production_app.main

Or from the command line:
    python video_production_app/main.py
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from video_production_app.ui.app import VideoProductionApp


def main():
    """
    Main entry point for the Video Production App.
    
    This function creates and runs the main application window.
    It handles any initialization that needs to happen before
    the UI is created and started.
    
    Example:
        if __name__ == "__main__":
            main()
    """
    try:
        # Create and run the application
        app = VideoProductionApp()
        app.mainloop()
        
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
