#!/usr/bin/env python3
"""
Standalone entry point for Tkinter UI (CustomTkinter-based).

This file allows you to launch the Tkinter UI directly without using the launcher.
Simply run: python -m video_production_app.entry_points.tkinter_ui

The Tkinter UI provides a classic desktop interface with advanced features like:
- VLC video player integration
- Keyboard shortcuts
- Mouse wheel zoom
- Batch processing
"""

import sys
from pathlib import Path

def main():
    """Launch the Tkinter UI."""
    print("🖥️  Launching Tkinter UI...")
    print("=" * 50)
    
    try:
        # Add project root to path (go up one level: video_production_app -> root)
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # Import and run the Tkinter UI
        from video_production_app.ui.app import VideoProductionApp
        
        app = VideoProductionApp()
        app.mainloop()
        
    except ImportError as e:
        print(f"❌ Error: Could not import Tkinter UI dependencies.")
        print(f"   Make sure CustomTkinter is installed: pip install customtkinter")
        print(f"   Error details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error launching Tkinter UI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

